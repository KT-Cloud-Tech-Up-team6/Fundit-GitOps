#!/usr/bin/env python3
"""Send one fixed SSM document and report its final result without remote logs."""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPOSITORY = "https://github.com/KT-Cloud-Tech-Up-team6/Fundit-GitOps.git"
REGION = "ap-northeast-2"
DOCUMENT = "fundit-dev-deploy-gateway"
MIN_AGENT_VERSION = (3, 3, 2746, 0)
MONITOR_TIMEOUT = 1380


class DeploymentError(Exception):
    pass


def configuration(env, image_text):
    if env.get("DEPLOY_ENABLED") != "true" or env.get("DEPLOY_REF") != "refs/heads/main":
        raise DeploymentError("Deployment requires an enabled main-branch run.")
    sha = env.get("DEPLOY_GIT_SHA", "")
    instance = env.get("DEPLOY_INSTANCE_ID", "")
    version = env.get("DEPLOY_DOCUMENT_VERSION", "")
    role = re.fullmatch(r"arn:aws:iam::([0-9]{12}):role/fundit-dev-gitops-deploy-role",
                        env.get("DEPLOY_ROLE_ARN", ""))
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise DeploymentError("A full GitOps commit SHA is required.")
    if not re.fullmatch(r"i-([0-9a-f]{8}|[0-9a-f]{17})", instance):
        raise DeploymentError("Configure exactly one development EC2 instance ID.")
    if not role or not re.fullmatch(r"[1-9][0-9]*", version):
        raise DeploymentError("Configure the deployment role and a numeric SSM document version.")
    lines = [line for line in image_text.splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    prefix = "GATEWAY_IMAGE={}.dkr.ecr.{}.amazonaws.com/fundit-backend".format(role[1], REGION)
    if (len(lines) != 1 or not re.fullmatch(
            re.escape(prefix) + r"(:gateway-sha-[0-9a-f]{40}|:sha-[0-9a-f]{40}|@sha256:[0-9a-f]{64})",
            lines[0])):
        raise DeploymentError("Set the Gateway image to a full SHA tag or digest in the backend ECR.")
    return {"sha": sha, "instance": instance, "version": version, "account": role[1]}


def run_command(args):
    # SendCommand has no client idempotency token: do not blindly retry an ambiguous send.
    env = dict(os.environ, AWS_PAGER="", AWS_MAX_ATTEMPTS="1")
    try:
        return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, timeout=40, env=env)
    except (subprocess.TimeoutExpired, OSError):
        raise DeploymentError("Command unavailable or timed out; inspect SSM before retrying a deployment.")


def aws_json(args, runner, query, allow_not_found=False):
    result = runner(["aws"] + args + ["--region", REGION, "--output", "json",
                                      "--query", query, "--cli-connect-timeout", "10",
                                      "--cli-read-timeout", "20"])
    if result.returncode:
        if allow_not_found and "InvocationDoesNotExist" in result.stderr:
            return None
        # stderr or SSM stdout can contain server output: never relay it to Actions.
        raise DeploymentError("AWS {} failed; inspect the command in SSM before retrying.".format(args[1]))
    try:
        return json.loads(result.stdout)
    except ValueError:
        raise DeploymentError("AWS returned an invalid response.")


def deploy(config, runner=run_command, clock=time.monotonic, sleep=time.sleep):
    remote = runner(["git", "ls-remote", "--exit-code", REPOSITORY, "refs/heads/main"])
    refs = remote.stdout.split()
    if remote.returncode or len(refs) != 2 or refs != [config["sha"], "refs/heads/main"]:
        raise DeploymentError("main has changed or cannot be read; start a new run for the current main.")
    account = aws_json(["sts", "get-caller-identity"], runner, "Account")
    if account != config["account"]:
        raise DeploymentError("AWS account does not match the configured deployment role.")
    nodes = aws_json(["ssm", "describe-instance-information", "--filters",
                      "Key=InstanceIds,Values=" + config["instance"]], runner,
                     "InstanceInformationList[].{Id:InstanceId,Ping:PingStatus,Platform:PlatformType,Agent:AgentVersion}")
    if (not isinstance(nodes, list) or len(nodes) != 1 or
            nodes[0].get("Id") != config["instance"] or nodes[0].get("Ping") != "Online" or
            nodes[0].get("Platform") != "Linux"):
        raise DeploymentError("The configured Linux EC2 must be Online in Systems Manager.")
    agent = nodes[0].get("Agent", "")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+", agent) or tuple(map(int, agent.split("."))) < MIN_AGENT_VERSION:
        raise DeploymentError("SSM Agent 3.3.2746.0 or newer is required for ENV_VAR parameters.")
    command_id = aws_json([
        "ssm", "send-command", "--instance-ids", config["instance"],
        "--document-name", DOCUMENT, "--document-version", config["version"],
        "--parameters", json.dumps({"GitCommit": [config["sha"]]}),
        "--timeout-seconds", "60", "--max-concurrency", "1", "--max-errors", "0",
        "--comment", "Gateway GitOps " + config["sha"],
    ], runner, "Command.CommandId")
    if not isinstance(command_id, str) or not re.fullmatch(r"[0-9a-f-]{36}", command_id):
        raise DeploymentError("Missing SSM command ID; inspect SSM before retrying.")
    print("SSM command: {} (GitOps {})".format(command_id, config["sha"]), flush=True)
    started = clock()
    previous = None
    while clock() - started < MONITOR_TIMEOUT:
        result = aws_json(["ssm", "get-command-invocation", "--command-id", command_id,
                           "--instance-id", config["instance"], "--plugin-name", "deployGateway"],
                          runner, "{Status:Status,ResponseCode:ResponseCode}", allow_not_found=True)
        if result is None:
            if clock() - started >= 60:
                raise DeploymentError("SSM invocation did not become visible; inspect its command ID.")
        else:
            status = result.get("Status")
            if status != previous:
                print("SSM status: {}".format(status), flush=True)
                previous = status
            if status == "Success" and result.get("ResponseCode") == 0:
                print("Gateway deployment and local health check succeeded.")
                return command_id
            if status not in ("Pending", "InProgress", "Delayed", "Cancelling"):
                raise DeploymentError("SSM deployment failed ({}); previous containers may already be replaced.".format(status))
        sleep(10)
    raise DeploymentError("SSM monitoring timed out; do not assume cancellation or automatic rollback.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate local settings without contacting AWS.")
    args = parser.parse_args()
    try:
        image_file = Path(__file__).resolve().parent.parent / "compose/dev/images.env"
        config = configuration(os.environ, image_file.read_text())
        if args.check:
            print("Local deployment settings validated.")
        else:
            deploy(config)
    except (DeploymentError, OSError) as error:
        print("Deployment error: {}".format(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
