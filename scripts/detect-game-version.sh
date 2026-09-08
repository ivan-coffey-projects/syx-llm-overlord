#!/usr/bin/env bash
# Detect Songs of Syx major version folder (e.g. V69). Prints one line: V69
set -euo pipefail

if [[ -n "${SYX_GAME_VERSION:-}" ]]; then
  v="${SYX_GAME_VERSION}"
  [[ "${v}" == V* ]] || v="V${v}"
  echo "${v}"
  exit 0
fi

# Highest V* script folder under user mods
MODS="${HOME}/.local/share/songsofsyx/mods"
best_num=0
best_ver=""
if [[ -d "${MODS}" ]]; then
  while IFS= read -r -d '' dir; do
    base="$(basename "${dir}")"
    if [[ "${base}" =~ ^V([0-9]+)$ ]]; then
      num="${BASH_REMATCH[1]}"
      if (( num > best_num )); then
        best_num="${num}"
        best_ver="${base}"
      fi
    fi
  done < <(find "${MODS}" -mindepth 2 -maxdepth 2 -type d -name 'V*' -print0 2>/dev/null || true)
fi
if [[ -n "${best_ver}" ]]; then
  echo "${best_ver}"
  exit 0
fi

# Game install info/VERSION or similar
for root in \
  "${SONGSOFSYX_DIR:-}" \
  "${HOME}/.steam/steam/steamapps/common/Songs of Syx" \
  "${HOME}/.steam/steam/steamapps/common/Songs of Syx Demo" \
  "${HOME}/.local/share/Steam/steamapps/common/Songs of Syx" \
  "${HOME}/.local/share/Steam/steamapps/common/Songs of Syx Demo" \
  "${HOME}/GAMES/Steam/_steamapps/steamapps/common/Songs of Syx Demo" \
  "${HOME}/GAMES/Steam/_steamapps/steamapps/common/Songs of Syx"
do
  [[ -n "${root}" && -d "${root}" ]] || continue
  for f in "${root}/info/VERSION" "${root}/VERSION" "${root}/version.txt"; do
    if [[ -f "${f}" ]]; then
      line="$(head -1 "${f}" | tr -d '[:space:]')"
      if [[ "${line}" =~ ^V?[0-9]+ ]]; then
        [[ "${line}" == V* ]] && echo "${line}" || echo "V${line}"
        exit 0
      fi
    fi
  done
done

echo "V69"
