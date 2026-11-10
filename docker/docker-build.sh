#!/bin/bash
#
# Build the gtfsrdb Docker image.
#
# Image tag: the git tag pointing at HEAD if one exists, otherwise 'latest'.
# When a version tag is used, the image is also tagged 'latest' so that
# docker-run.sh (which looks for gtfsrdb:latest) picks up the newest build.
#
# Usage: docker-build.sh [extra docker build arguments]

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
image_name="gtfsrdb"

version="$(git -C "$repo_root" describe --tags --exact-match HEAD 2>/dev/null || true)"
if [[ -z "$version" ]]; then
  version="latest"
fi

tags=(-t "$image_name:$version")
if [[ "$version" != "latest" ]]; then
  tags+=(-t "$image_name:latest")
fi

echo "Building $image_name:$version"

docker build \
  -f "$script_dir/Dockerfile" \
  --build-arg VERSION="$version" \
  "${tags[@]}" \
  "$@" \
  "$repo_root"
