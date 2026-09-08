#!/usr/bin/env bash
# Find SongsOfSyx.jar — prints absolute path to stdout
set -euo pipefail

if [[ -n "${SONGSOFSYX_JAR:-}" && -f "${SONGSOFSYX_JAR}" ]]; then
  echo "$(cd "$(dirname "${SONGSOFSYX_JAR}")" && pwd)/$(basename "${SONGSOFSYX_JAR}")"
  exit 0
fi

if [[ -n "${SONGSOFSYX_DIR:-}" && -f "${SONGSOFSYX_DIR}/SongsOfSyx.jar" ]]; then
  echo "$(cd "${SONGSOFSYX_DIR}" && pwd)/SongsOfSyx.jar"
  exit 0
fi

SEARCH=(
  "${HOME}/.steam/steam/steamapps/common/Songs of Syx/SongsOfSyx.jar"
  "${HOME}/.steam/steam/steamapps/common/Songs of Syx Demo/SongsOfSyx.jar"
  "${HOME}/.local/share/Steam/steamapps/common/Songs of Syx/SongsOfSyx.jar"
  "${HOME}/.local/share/Steam/steamapps/common/Songs of Syx Demo/SongsOfSyx.jar"
  "${HOME}/GAMES/Steam/_steamapps/steamapps/common/Songs of Syx/SongsOfSyx.jar"
  "${HOME}/GAMES/Steam/_steamapps/steamapps/common/Songs of Syx Demo/SongsOfSyx.jar"
)

for jar in "${SEARCH[@]}"; do
  if [[ -f "${jar}" ]]; then
    echo "$(cd "$(dirname "${jar}")" && pwd)/$(basename "${jar}")"
    exit 0
  fi
done

# Steam library scan
for lib in "${HOME}/.steam/steam/steamapps/libraryfolders.vdf" \
           "${HOME}/.local/share/Steam/steamapps/libraryfolders.vdf"; do
  [[ -f "${lib}" ]] || continue
  while IFS= read -r path; do
    for name in "Songs of Syx" "Songs of Syx Demo"; do
      candidate="${path}/${name}/SongsOfSyx.jar"
      if [[ -f "${candidate}" ]]; then
        echo "$(cd "$(dirname "${candidate}")" && pwd)/$(basename "${candidate}")"
        exit 0
      fi
    done
  done < <(grep -oP '"path"\s+"\K[^"]+' "${lib}" 2>/dev/null || true)
done

echo "ERROR: SongsOfSyx.jar not found. Set SONGSOFSYX_JAR or SONGSOFSYX_DIR." >&2
exit 1
