#!/usr/bin/env bash
# First-time setup for Syx LLM Overlord
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "${ROOT}"

echo "== Syx LLM Overlord — install =="

# shellcheck source=/dev/null
[[ -f "${ROOT}/.env" ]] && source "${ROOT}/.env"

need() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1" >&2; exit 1; }
}

need java
need python3

JAVA_VER="$(java -version 2>&1 | head -1 || true)"
echo "Java: ${JAVA_VER}"

JAR="$("${ROOT}/scripts/find-game-jar.sh")"
GAME_DIR="$(dirname "${JAR}")"
GAME_VERSION="$("${ROOT}/scripts/detect-game-version.sh")"
GAME_MAJOR="${GAME_VERSION#V}"

echo "Game JAR: ${JAR}"
echo "Game version folder: ${GAME_VERSION}"

export SONGSOFSYX_JAR="${JAR}"
export SONGSOFSYX_DIR="${GAME_DIR}"
export SYX_GAME_VERSION="${GAME_VERSION}"

# Python venv
VENV="${ROOT}/.venv"
if [[ ! -d "${VENV}" ]]; then
  python3 -m venv "${VENV}"
fi
# shellcheck source=/dev/null
source "${VENV}/bin/activate"
pip install -q -U pip
pip install -q -r "${ROOT}/bridge/requirements.txt"

# Bridge config
if [[ ! -f "${ROOT}/bridge/config.yaml" ]]; then
  cp "${ROOT}/bridge/config.example.yaml" "${ROOT}/bridge/config.yaml"
  echo "Created bridge/config.yaml — edit LLM provider before first run."
fi

if [[ ! -f "${ROOT}/.env" ]]; then
  cp "${ROOT}/.env.example" "${ROOT}/.env"
  echo "Created .env — add OPENROUTER_API_KEY or use Ollama (see README)."
fi

# Update mod metadata major version
INFO="${ROOT}/syx-llm-mod/_Info.txt"
if [[ -f "${INFO}" ]]; then
  sed -i "s/GAME_VERSION_MAJOR: [0-9]*/GAME_VERSION_MAJOR: ${GAME_MAJOR}/" "${INFO}"
fi

# Build mod
echo "Building mod for ${GAME_VERSION}..."
(
  cd "${ROOT}/syx-llm-mod"
  chmod +x mvnw 2>/dev/null || true
  ./mvnw install -P linux -q \
    -Dgame.jar.path="${JAR}" \
    -Dgame.script.dir="${GAME_DIR}/base/script" \
    -Dgame.version.major="${GAME_VERSION}"
)

MOD_JAR="${HOME}/.local/share/songsofsyx/mods/syx-llm-overlord/${GAME_VERSION}/script/002_LLM_Overlord.jar"
if [[ ! -f "${MOD_JAR}" ]]; then
  echo "ERROR: mod build failed — expected ${MOD_JAR}" >&2
  exit 1
fi

mkdir -p "${ROOT}/logs"

cat <<EOF

Install complete.

Next steps:
  1. Edit ${ROOT}/.env — set OPENROUTER_API_KEY and/or configure Ollama in bridge/config.yaml
  2. Run: ${ROOT}/run.sh
  3. In Songs of Syx launcher: enable "LLM Overlord" mod → Play → new/random game
  4. Dashboard: http://localhost:3847

Optional personal launcher: see docs/PERSONAL-LAUNCHER.md

EOF
