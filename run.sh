#!/usr/bin/env bash
# Minimal launcher — build mod if needed, start bridge, print game instructions.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "${ROOT}"

MODE="${1:-all}"

# shellcheck source=/dev/null
[[ -f "${ROOT}/.env" ]] && source "${ROOT}/.env"

export SYX_OVERLORD_ROOT="${ROOT}"
export SYX_RESTART_SCRIPT="${ROOT}/scripts/restart-game-only.sh"

log() { printf '[syx-overlord] %s\n' "$*"; }

ensure_mod() {
  local ver jar mod_jar
  ver="$("${ROOT}/scripts/detect-game-version.sh")"
  mod_jar="${HOME}/.local/share/songsofsyx/mods/syx-llm-overlord/${ver}/script/002_LLM_Overlord.jar"
  if [[ -f "${mod_jar}" ]]; then
    log "Mod OK: ${mod_jar}"
    return 0
  fi
  log "Mod missing — running install.sh (mod build only)..."
  JAR="$("${ROOT}/scripts/find-game-jar.sh")"
  export SONGSOFSYX_JAR="${JAR}"
  export SONGSOFSYX_DIR="$(dirname "${JAR}")"
  export SYX_GAME_VERSION="${ver}"
  (
    cd "${ROOT}/syx-llm-mod"
    ./mvnw install -P linux -q \
      -Dgame.jar.path="${JAR}" \
      -Dgame.script.dir="${SONGSOFSYX_DIR}/base/script" \
      -Dgame.version.major="${SYX_GAME_VERSION}"
  )
}

start_bridge() {
  local port="${SYX_BRIDGE_PORT:-3847}"
  if curl -sf "http://localhost:${port}/api/health" >/dev/null 2>&1; then
    log "Bridge already running on :${port}"
    return 0
  fi

  VENV="${ROOT}/.venv"
  if [[ ! -d "${VENV}" ]]; then
    log "Run ./install.sh first"
    exit 1
  fi

  # An IDE AppImage can hijack .venv/bin/python — use system Python + venv site-packages.
  BRIDGE_PY="/usr/bin/python3.14"
  if [[ ! -x "${BRIDGE_PY}" ]]; then
    BRIDGE_PY="$(command -v python3.14 || command -v python3)"
  fi
  PY_VER="$("${BRIDGE_PY}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  VENV_SITE="${VENV}/lib/python${PY_VER}/site-packages"
  if [[ ! -d "${VENV_SITE}" ]]; then
    log "WARN: ${VENV_SITE} missing — run ./install.sh"
    exit 1
  fi

  mkdir -p "${ROOT}/logs"
  export SYX_BRIDGE_PORT="${port}"
  export PYTHONPATH="${VENV_SITE}${PYTHONPATH:+:${PYTHONPATH}}"
  cd "${ROOT}/bridge"
  nohup "${BRIDGE_PY}" -m bridge >>"${ROOT}/logs/bridge.log" 2>&1 &
  echo $! >"${ROOT}/logs/bridge.pid"
  log "Bridge starting (PID $(cat "${ROOT}/logs/bridge.pid")) — log: ${ROOT}/logs/bridge.log"

  for _ in $(seq 1 30); do
    if curl -sf "http://localhost:${port}/api/health" >/dev/null 2>&1; then
      log "Bridge ready: http://localhost:${port}"
      return 0
    fi
    sleep 1
  done
  log "WARN: bridge not responding yet — check ${ROOT}/logs/bridge.log"
}

watch_bridge() {
  local port="${SYX_BRIDGE_PORT:-3847}"
  local interval="${SYX_BRIDGE_WATCH_SEC:-30}"
  log "Bridge watchdog — checking :${port} every ${interval}s (Ctrl+C to stop)"
  while true; do
    if ! curl -sf "http://localhost:${port}/api/health" >/dev/null 2>&1; then
      log "Bridge down — restarting"
      start_bridge || log "WARN: restart failed"
    fi
    sleep "${interval}"
  done
}

case "${MODE}" in
  build)
    ensure_mod
    ;;
  bridge)
    start_bridge
    ;;
  watch)
    watch_bridge
    ;;
  all|"")
    ensure_mod
    start_bridge
    JAR="$("${ROOT}/scripts/find-game-jar.sh" 2>/dev/null || true)"
    cat <<EOF

Launch Songs of Syx manually from Steam, then:
  1. Enable mod: LLM Overlord
  2. Play → random game → go!
  3. Open dashboard: http://localhost:3847
  4. Talk to the overlord in the dashboard chat panel

Game path: ${JAR:-not found — set SONGSOFSYX_JAR in .env}
Stop bridge: kill \$(cat ${ROOT}/logs/bridge.pid)

EOF
    if command -v xdg-open >/dev/null 2>&1; then
      xdg-open "http://localhost:3847" 2>/dev/null || true
    fi
    ;;
  -h|--help)
    cat <<EOF
Usage: ./run.sh [all|build|bridge|watch]

  all     Build mod if needed, start bridge, print instructions (default)
  build   Build/install mod only
  bridge  Start Python bridge only
  watch   Keep bridge alive — restart if health check fails

EOF
    ;;
  *)
    echo "Unknown mode: ${MODE} (try --help)" >&2
    exit 1
    ;;
esac
