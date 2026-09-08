#!/bin/bash
# Reset Songs of Syx display settings when the game renders in the bottom-left corner.
SETTINGS="$HOME/.local/share/songsofsyx/settings/LauncherSettings.txt"

if [ ! -f "$SETTINGS" ]; then
    echo "Settings not found: $SETTINGS"
    exit 1
fi

cp "$SETTINGS" "${SETTINGS}.bak.$(date +%s)"

python3 <<'PY'
from pathlib import Path
import re

path = Path.home() / ".local/share/songsofsyx/settings/LauncherSettings.txt"
text = path.read_text()

# SCREEN_MODE: 0=borderless (broken on Linux), 1=fullscreen, 2=windowed
fixes = {
    "SCREEN_MODE": "1",
    "WINDOW_WIDTH": "20",
    "WIDOW_HEIGHT": "20",
    "WIDOW_SCALE": "100",
    "WINDOW_DECORATE": "1",
    "WINDOW_FLOAT": "0",
    "WINDOW_FULL_FULL": "1",
    "FULL_DISPLAY": "0",
}

for key, val in fixes.items():
    text, n = re.subn(rf"^{re.escape(key)}: .*", f"{key}: {val},", text, count=1, flags=re.M)
    if n == 0:
        print(f"warn: {key} not found")

path.write_text(text)
print(f"Fixed display settings in {path}")
print("Using fullscreen (SCREEN_MODE=1). Restart the game.")
PY
