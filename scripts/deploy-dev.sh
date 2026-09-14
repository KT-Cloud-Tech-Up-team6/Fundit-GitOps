#!/usr/bin/env bash
# Run on the development EC2. This script does not establish SSH/SSM access.
set +x
set -euo pipefail

die() { printf '[deploy-dev] ERROR: %s\n' "$*" >&2; exit 1; }
info() { printf '[deploy-dev] %s\n' "$*"; }
require_command() { command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"; }

check_only=false
case "${1:-}" in
  --help|-h)
    printf 'Usage: bash scripts/deploy-dev.sh [--check] /absolute/path/to/gateway.env\n'
    printf 'Without --check, this logs into ECR and updates the development gateway.\n'
    exit 0
    ;;
  --check) check_only=true; shift ;;
esac
[[ $# -eq 1 ]] || die 'Provide one absolute path to the server runtime env file; see --help.'

for tool in docker realpath stat; do require_command "$tool"; done
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
images_file="$repo_root/compose/dev/images.env"
compose_file="$repo_root/compose/dev/compose.yaml"

# Do not source env files or allow an inherited image variable to override Git.
gateway_image=''
while IFS= read -r line || [[ -n "$line" ]]; do
  [[ "$line" =~ ^[[:space:]]*(#|$) ]] && continue
  if [[ "$line" =~ ^GATEWAY_IMAGE=([^[:space:]]+)$ && -z "$gateway_image" ]]; then
    gateway_image=${BASH_REMATCH[1]}
  else
    die 'images.env must contain exactly one unquoted GATEWAY_IMAGE assignment.'
  fi
done < "$images_file"
image_pattern='^[0-9]{12}\.dkr\.ecr\.([a-z0-9-]+)\.amazonaws\.com/[a-z0-9][a-z0-9._/-]*(:([a-z0-9-]+-)?sha-[0-9a-f]{40}|@sha256:[0-9a-f]{64})$'
[[ "$gateway_image" =~ $image_pattern ]] || die 'Set a private ECR image URI with a full SHA tag or digest in images.env.'
aws_region=${BASH_REMATCH[1]}
export GATEWAY_IMAGE="$gateway_image"

[[ "$1" == /* && -f "$1" && -r "$1" ]] || die 'Runtime env file must be an existing readable absolute path.'
runtime_file=$(realpath -- "$1")
[[ "$runtime_file" != "$repo_root/"* ]] || die 'Keep the runtime env file outside the Git checkout.'
runtime_mode=$(stat -c '%a' -- "$runtime_file")
(( (8#$runtime_mode & 077) == 0 )) || die 'Runtime env file must have no group/other permissions (use mode 600).'

# Match the raw env_file contract. Reject missing/duplicate keys without printing values.
declare -A runtime_keys=()
while IFS= read -r line || [[ -n "$line" ]]; do
  [[ "$line" =~ ^[[:space:]]*(#|$) ]] && continue
  [[ "$line" =~ ^([A-Z_][A-Z0-9_]*)=(.*)$ && "$line" != *$'\r'* ]] || die 'Runtime env file must use KEY=value lines with Unix line endings.'
  key=${BASH_REMATCH[1]}
  value=${BASH_REMATCH[2]}
  [[ -z "${runtime_keys[$key]:-}" ]] || die 'Runtime env file contains a duplicate key.'
  [[ "$value" =~ [^[:space:]] ]] || die 'All four runtime values must be nonempty.'
  case "$key" in
    AUTH_SERVICE_BASE_URL|MEMBER_SERVICE_BASE_URL|PAYMENT_SERVICE_BASE_URL)
      [[ "$value" =~ ^https?://[^[:space:]]+$ ]] || die 'Service base URLs must be absolute HTTP(S) URLs.'
      ;;
    INTERNAL_API_KEY) ;;
    *) die 'Runtime env file contains an unsupported key; use runtime.env.example.' ;;
  esac
  runtime_keys[$key]=present
done < "$runtime_file"
for key in AUTH_SERVICE_BASE_URL MEMBER_SERVICE_BASE_URL PAYMENT_SERVICE_BASE_URL INTERNAL_API_KEY; do
  [[ -n "${runtime_keys[$key]:-}" ]] || die "Missing required runtime key: $key"
done
unset line value
export GATEWAY_RUNTIME_ENV_FILE="$runtime_file"

export GATEWAY_BIND_ADDRESS="${GATEWAY_BIND_ADDRESS:-127.0.0.1}"
export GATEWAY_HOST_PORT="${GATEWAY_HOST_PORT:-8080}"
case "$GATEWAY_BIND_ADDRESS" in
  127.0.0.1|0.0.0.0) ;;
  *) die 'GATEWAY_BIND_ADDRESS must be 127.0.0.1 or 0.0.0.0.' ;;
esac
[[ "$GATEWAY_HOST_PORT" =~ ^[1-9][0-9]{0,4}$ ]] && (( GATEWAY_HOST_PORT <= 65535 )) || die 'GATEWAY_HOST_PORT must be between 1 and 65535.'
health_timeout=${HEALTH_TIMEOUT_SECONDS:-120}
[[ "$health_timeout" =~ ^[1-9][0-9]{0,2}$ ]] && (( health_timeout <= 600 )) || die 'HEALTH_TIMEOUT_SECONDS must be between 1 and 600.'

compose_version=$(docker compose version --short 2>/dev/null) || die 'Docker Compose plugin is required.'
[[ "$compose_version" =~ ^v?([0-9]+)\.([0-9]+)\.([0-9]+) ]] || die 'Unable to determine Docker Compose version.'
(( BASH_REMATCH[1] > 2 || (BASH_REMATCH[1] == 2 && BASH_REMATCH[2] >= 30) )) || die 'Docker Compose 2.30.0 or newer is required for raw env files.'
compose=(docker compose --project-name fundit-dev --env-file "$images_file" -f "$compose_file")
"${compose[@]}" config --quiet >/dev/null 2>&1 || die 'Compose validation failed. Check the template, file paths, and Compose version; no configuration values were logged.'
if "$check_only"; then
  info 'Configuration validated. No AWS login, image pull, or container changes performed.'
  exit 0
fi

for tool in aws curl flock mktemp; do require_command "$tool"; done
aws --version 2>&1 | grep -q '^aws-cli/2\.' || die 'AWS CLI v2 is required.'
[[ -z "${DOCKER_CONTEXT:-}" && ( -z "${DOCKER_HOST:-}" || "$DOCKER_HOST" == unix://* ) ]] || die 'Deployment requires a local Docker daemon without a named DOCKER_CONTEXT.'
lock_file=${DEPLOY_LOCK_FILE:-/var/lib/fundit/deploy/dev.lock}
[[ "$lock_file" == /* && -d "$(dirname -- "$lock_file")" ]] || die 'Provision the deployment lock directory first; see README.'
exec 9>"$lock_file"
flock -n 9 || die 'Another development deployment is in progress.'

# ECR credentials live only in this temporary Docker config, never in Git.
docker_config_dir=$(mktemp -d /tmp/fundit-dev-docker.XXXXXX)
cleanup() { rm -rf -- "$docker_config_dir"; }
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
export DOCKER_CONFIG="$docker_config_dir"
docker info >/dev/null 2>&1 || die 'Docker daemon is unavailable to this deployment user.'
registry=${gateway_image%%/*}
info 'Logging into ECR using the AWS credential chain.'
if ! aws ecr get-login-password --region "$aws_region" 2>/dev/null |
  docker login --username AWS --password-stdin "$registry" >/dev/null 2>&1; then
  die 'ECR login failed. Check the EC2 role, repository access, region, and network.'
fi

info 'Pulling the configured gateway image.'
"${compose[@]}" pull gateway || die 'Image pull failed; running containers were not updated.'
info 'Updating the gateway container.'
"${compose[@]}" up -d --no-build --pull never --no-deps gateway || die 'Compose update failed. Inspect the gateway state before retrying; see README.'
container_id=$("${compose[@]}" ps --all --quiet gateway)
[[ -n "$container_id" && "$container_id" != *$'\n'* ]] || die 'Expected exactly one gateway container after deployment.'

info 'Waiting for gateway /actuator/health to return HTTP 200.'
deadline=$((SECONDS + health_timeout))
while (( SECONDS < deadline )); do
  remaining=$((deadline - SECONDS))
  (( remaining > 0 )) || break
  request_timeout=5
  (( remaining >= request_timeout )) || request_timeout=$remaining
  status=$(docker inspect --format '{{.State.Status}}' "$container_id" 2>/dev/null) || status=unknown
  if [[ "$status" == running ]]; then
    http_code=$(curl --noproxy '*' --silent --output /dev/null --write-out '%{http_code}' \
      --connect-timeout "$request_timeout" --max-time "$request_timeout" \
      "http://127.0.0.1:${GATEWAY_HOST_PORT}/actuator/health") || http_code=000
    if [[ "$http_code" == 200 ]]; then
      info 'Gateway deployment passed the local health check.'
      exit 0
    fi
  fi
  sleep 2
done
die 'Gateway health check timed out. Deployment failed; use the last successful image for manual recovery. See README.'
