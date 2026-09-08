#!/bin/bash
# Watch for Songs of Syx demo installation and extract the JAR path
echo "Watching for Songs of Syx installation..."
echo "Steam apps directories:"

SEARCH_DIRS=(
    "$HOME/.steam/steam/steamapps/common"
    "$HOME/.local/share/Steam/steamapps/common"
)

while true; do
    for dir in "${SEARCH_DIRS[@]}"; do
        if [ -d "$dir/Songs of Syx" ]; then
            echo ""
            echo "=== FOUND: $dir/Songs of Syx ==="
            ls -la "$dir/Songs of Syx/" | head -20
            echo ""
            if [ -f "$dir/Songs of Syx/SongsOfSyx.jar" ]; then
                echo "SongsOfSyx.jar found!"
                echo "Size: $(du -h "$dir/Songs of Syx/SongsOfSyx.jar" | cut -f1)"
            fi
            if [ -f "$dir/Songs of Syx/info/SongsOfSyx-sources.jar" ]; then
                echo "SongsOfSyx-sources.jar found!"
            fi
            exit 0
        fi
    done
    sleep 5
done
