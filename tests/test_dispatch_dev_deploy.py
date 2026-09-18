import json
import os
import sys
import unittest
import importlib.util
from types import SimpleNamespace

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "dispatch-dev-deploy.py")
SPEC = importlib.util.spec_from_file_location("dispatch_dev_deploy", SCRIPT)
deployer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(deployer)


SHA = "a" * 40
INSTANCE = "i-0123456789abcdef0"
ROLE = "arn:aws:iam::123456789012:role/fundit-dev-gitops-deploy-role"
IMAGE = "GATEWAY_IMAGE=123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/fundit-backend:gateway-sha-" + SHA


def result(stdout="", returncode=0, stderr=""):
    return SimpleNamespace(stdout=stdout, returncode=returncode, stderr=stderr)


def environment(**overrides):
    values = {
        "DEPLOY_ENABLED": "true",
        "DEPLOY_REF": "refs/heads/main",
        "DEPLOY_GIT_SHA": SHA,
        "DEPLOY_INSTANCE_ID": INSTANCE,
        "DEPLOY_ROLE_ARN": ROLE,
        "DEPLOY_DOCUMENT_VERSION": "1",
    }
    values.update(overrides)
    return values


class Clock(object):
    def __init__(self):
        self.value = 0

    def now(self):
        return self.value

    def sleep(self, seconds):
        self.value += seconds


class Runner(object):
    def __init__(self, statuses=None, node=None, account="123456789012"):
        self.calls = []
        self.statuses = list(statuses or [{"Status": "Success", "ResponseCode": 0}])
        self.node = node or {"Id": INSTANCE, "Ping": "Online", "Platform": "Linux", "Agent": "3.3.2746.0"}
        self.account = account

    def __call__(self, args):
        self.calls.append(args)
        if args[0] == "git":
            return result(SHA + "\trefs/heads/main\n")
        action = args[2]
        if action == "get-caller-identity":
            return result(json.dumps(self.account))
        if action == "describe-instance-information":
            return result(json.dumps([self.node]))
        if action == "send-command":
            return result(json.dumps("11111111-1111-1111-1111-111111111111"))
        if action == "get-command-invocation":
            value = self.statuses.pop(0) if self.statuses else {"Status": "InProgress", "ResponseCode": -1}
            if value is None:
                return result("", 255, "InvocationDoesNotExist")
            return result(json.dumps(value))
        raise AssertionError("unexpected command: {}".format(args))


class DispatchDeploymentTests(unittest.TestCase):
    def test_configuration_requires_enabled_main_and_pinned_gateway_image(self):
        config = deployer.configuration(environment(), IMAGE)
        self.assertEqual(config["sha"], SHA)
        with self.assertRaises(deployer.DeploymentError):
            deployer.configuration(environment(DEPLOY_ENABLED="false"), IMAGE)
        with self.assertRaises(deployer.DeploymentError):
            deployer.configuration(environment(), "GATEWAY_IMAGE=REPLACE_WITH_ECR_IMAGE_URI")

    def test_offline_instance_never_sends_command(self):
        runner = Runner(node={"Id": INSTANCE, "Ping": "Offline", "Platform": "Linux", "Agent": "3.3.2746.0"})
        with self.assertRaises(deployer.DeploymentError):
            deployer.deploy(deployer.configuration(environment(), IMAGE), runner=runner)
        self.assertFalse(any(call[2] == "send-command" for call in runner.calls if call[0] == "aws"))

    def test_old_agent_never_sends_command(self):
        runner = Runner(node={"Id": INSTANCE, "Ping": "Online", "Platform": "Linux", "Agent": "3.3.2745.0"})
        with self.assertRaises(deployer.DeploymentError):
            deployer.deploy(deployer.configuration(environment(), IMAGE), runner=runner)
        self.assertFalse(any(call[2] == "send-command" for call in runner.calls if call[0] == "aws"))

    def test_dispatches_only_fixed_document_and_commit_after_preflight(self):
        runner = Runner(statuses=[None, {"Status": "InProgress", "ResponseCode": -1}, {"Status": "Success", "ResponseCode": 0}])
        clock = Clock()
        command_id = deployer.deploy(deployer.configuration(environment(), IMAGE), runner=runner,
                                     clock=clock.now, sleep=clock.sleep)
        self.assertEqual(command_id, "11111111-1111-1111-1111-111111111111")
        send = [call for call in runner.calls if call[0] == "aws" and call[2] == "send-command"]
        self.assertEqual(len(send), 1)
        self.assertIn(deployer.DOCUMENT, send[0])
        parameters = json.loads(send[0][send[0].index("--parameters") + 1])
        self.assertEqual(parameters, {"GitCommit": [SHA]})
        self.assertIn(INSTANCE, send[0])
        self.assertNotIn("AWS-RunShellScript", send[0])

    def test_failed_ssm_status_fails_without_relaying_remote_output(self):
        runner = Runner(statuses=[{"Status": "Failed", "ResponseCode": 1}])
        with self.assertRaises(deployer.DeploymentError) as raised:
            deployer.deploy(deployer.configuration(environment(), IMAGE), runner=runner)
        self.assertNotIn("secret", str(raised.exception).lower())


if __name__ == "__main__":
    unittest.main()
