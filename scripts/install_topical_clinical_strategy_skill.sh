#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CODEX_HOME_DIR="${CODEX_HOME:-$HOME/.codex}"
SOURCE_DIR="$REPO_ROOT/飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy"
TARGET_DIR="$CODEX_HOME_DIR/skills/topical-clinical-strategy"

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "Skill source directory not found: $SOURCE_DIR" >&2
  exit 1
fi

rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"
cp -R "$SOURCE_DIR"/. "$TARGET_DIR"/

echo "Installed skill to $TARGET_DIR"
