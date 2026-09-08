#!/usr/bin/env bash
# Restart Songs of Syx using the game installation detected by find-game-jar.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="${ROOT}/logs/restart-game.log"
mkdir -p "${ROOT}/logs"

# shellcheck source=/dev/null
[[ -f "${ROOT}/.env" ]] && source "${ROOT}/.env"

JAR="$("${ROOT}/scripts/find-game-jar.sh")"
GAME="$(dirname "${JAR}")"
GAME_LAUNCHER="${GAME}/LinuxNvidiaFix.sh"

log() { printf '[%s] %s\n' "$(date '+%H:%M:%S')" "$*" | tee -a "${LOG}"; }

pkill -f 'SongsOfSyx.jar|songsofsyx' 2>/dev/null || true
pkill -f 'LinuxNvidiaFix' 2>/dev/null || true
sleep 2

if [[ -x "${GAME_LAUNCHER}" ]]; then
  cd "${GAME}"
  setsid env DISPLAY="${DISPLAY:-:0}" "${GAME_LAUNCHER}" >>"${ROOT}/logs/launch.log" 2>&1 &
  log "game PID $!"
elif [[ -f "${JAR}" ]]; then
  cd "${GAME}"
  setsid env DISPLAY="${DISPLAY:-:0}" java -jar "${JAR}" >>"${ROOT}/logs/launch.log" 2>&1 &
  log "game PID $!"
else
  log "ERROR: cannot launch Songs of Syx"
  exit 1
fi

log "done — bridge stays up"
