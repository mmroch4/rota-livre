#!/usr/bin/env bash
# Vendors the official Coreflux agent skills (MIT) into .claude/skills/, pinned to the
# broker version we run, so every teammate gets them from git with no install step.
#
#   scripts/sync_skills.sh            # uses the default tag below
#   scripts/sync_skills.sh 2.22.1     # after bumping BROKER_IMAGE
#
# Source: https://github.com/CorefluxCommunity/coreflux-skills (tags match broker releases)
set -euo pipefail

TAG="${1:-2.22.0}"
REPO_ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
DEST="$REPO_ROOT/.claude/skills"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

curl -fsSL "https://codeload.github.com/CorefluxCommunity/coreflux-skills/tar.gz/refs/tags/$TAG" \
    | tar -xz -C "$TMP" --strip-components=1

for skill in "$TMP"/skills/*/; do
    name="$(basename "$skill")"
    rm -rf "${DEST:?}/$name"
    mkdir -p "$DEST/$name"
    cp -R "$skill". "$DEST/$name/"
    cp "$TMP/LICENSE" "$DEST/$name/LICENSE"
    echo "synced $name"
done
echo "$TAG" > "$DEST/.coreflux-skills-version"
echo "Coreflux skills $TAG -> ${DEST#"$REPO_ROOT"/}"
