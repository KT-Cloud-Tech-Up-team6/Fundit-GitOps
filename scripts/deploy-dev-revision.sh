#!/usr/bin/env bash
# Install a reviewed copy as /usr/local/libexec/fundit/deploy-dev-revision.
set +x
set -euo pipefail
umask 077

die() { printf '[dev-revision] ERROR: %s\n' "$*" >&2; exit 1; }
[[ $# -eq 1 && "$1" =~ ^[0-9a-f]{40}$ ]] || die 'Provide one full GitOps commit SHA.'
[[ $(id -un) == fundit-deploy ]] || die 'Run as the dedicated fundit-deploy user.'
for tool in git timeout flock mktemp; do
  command -v "$tool" >/dev/null 2>&1 || die "Required command not found: $tool"
done

revision=$1
deploy_root=/var/lib/fundit/deploy
runtime_file=/etc/fundit/dev/gateway.env
repository=https://github.com/KT-Cloud-Tech-Up-team6/Fundit-GitOps.git
[[ -d "$deploy_root/releases" && -w "$deploy_root/releases" ]] || die 'Provision the release directory first.'
[[ -r "$runtime_file" ]] || die 'Provision the server-only runtime file first.'

# This outer lock also covers Git checkout and the success record. deploy-dev.sh
# retains its existing dev.lock so local/manual deploys share the container lock.
exec 8>"$deploy_root/revision.lock"
flock -n 8 || die 'Another revision deployment is in progress.'
release=$(mktemp -d "$deploy_root/releases/run.XXXXXXXX")
export GIT_TERMINAL_PROMPT=0
if ! timeout --kill-after=10s 120s git -c credential.helper= clone --quiet \
  --depth=1 --single-branch --branch main "$repository" "$release/repo" 2>/dev/null; then
  die 'Unable to fetch the public GitOps main branch.'
fi
actual=$(git -C "$release/repo" rev-parse HEAD)
[[ "$actual" == "$revision" ]] || die 'main changed after dispatch; start a new workflow run.'

# Runtime values never travel through SSM. The current manual-deploy defaults
# (loopback port 8080, 120 second health timeout) are fixed for this initial path.
export GATEWAY_BIND_ADDRESS=127.0.0.1
export GATEWAY_HOST_PORT=8080
export HEALTH_TIMEOUT_SECONDS=120
export DEPLOY_LOCK_FILE="$deploy_root/dev.lock"
if ! timeout --kill-after=30s 900s bash "$release/repo/scripts/deploy-dev.sh" "$runtime_file"; then
  die 'Deployment failed. Inspect container state; failure does not roll back the image.'
fi

# Write only after health success; retain each checkout for investigation.
# Cleanup of old release directories is an explicit server maintenance task.
printf '%s\n' "$revision" > "$release/gitops-sha"
cp -- "$release/repo/compose/dev/images.env" "$release/images.env"
record=$(mktemp "$deploy_root/.last-success.XXXXXXXX")
printf '%s\n' "$release" > "$record"
mv -- "$record" "$deploy_root/last-success"
printf '[dev-revision] Deployed GitOps revision %s\n' "$revision"
