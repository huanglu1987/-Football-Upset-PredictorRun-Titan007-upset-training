#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CODEX_HOME_DIR="${CODEX_HOME:-$HOME/.codex}"
TARGET_DIR="$CODEX_HOME_DIR/skills/football-upset-predictor"

mkdir -p "$TARGET_DIR"
cp "$REPO_ROOT/skills/football-upset-predictor/SKILL.md" "$TARGET_DIR/SKILL.md"

echo "Installed skill to $TARGET_DIR/SKILL.md"
