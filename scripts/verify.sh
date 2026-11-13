#!/usr/bin/env bash
# The gates CI enforces, run exactly as CI runs them. CI's `test` job calls this
# script, and the pre-push hook calls it with --image, so a push that passes
# locally passes remotely.
#
#   scripts/verify.sh           lint, tests, workflow audits
#   scripts/verify.sh --image   ...and build the container image (CI's `image` job)
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

# renovate: datasource=docker depName=rhysd/actionlint
ACTIONLINT_IMAGE="rhysd/actionlint:1.7.12@sha256:b1934ee5f1c509618f2508e6eb47ee0d3520686341fec936f3b79331f9315667"

build_image=false
case "${1:-}" in
  "") ;;
  --image) build_image=true ;;
  *) echo "usage: $0 [--image]" >&2; exit 2 ;;
esac

step() { printf '\n==> %s\n' "$*"; }

step "uv sync --locked"
uv sync --locked --python 3.13 --quiet

step "ruff check"
uv run --locked ruff check .

step "pytest"
uv run --locked pytest -q

step "zizmor (workflow security)"
if [ -n "${GITHUB_ACTIONS:-}" ]; then
  uv run --locked zizmor --offline --format=github .github/workflows
else
  uv run --locked zizmor --offline .github/workflows
fi

step "actionlint"
docker run --rm -v "$PWD:/repo:ro" -w /repo "$ACTIONLINT_IMAGE" -color=false

if "$build_image"; then
  step "docker build"
  docker build --quiet --platform linux/amd64 -t icloud-mcp:verify . >/dev/null
fi

printf '\nAll checks passed.\n'
