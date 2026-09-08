#!/bin/bash
# Inspect SongsOfSyx JAR to find real class signatures for the LLM Overlord mod.
# Usage: ./inspect-jar.sh /path/to/SongsOfSyx.jar

JAR="${1:-SongsOfSyx.jar}"

if [ ! -f "$JAR" ]; then
    echo "Usage: $0 <path-to-SongsOfSyx.jar>"
    echo ""
    echo "Looking for SongsOfSyx.jar in common locations..."
    find /home -maxdepth 6 -name "SongsOfSyx.jar" 2>/dev/null | head -5
    exit 1
fi

echo "=== Inspecting: $JAR ==="
echo ""

echo "=== Key singletons and their methods ==="
echo ""

# game.GAME
echo "--- game.GAME ---"
jar tf "$JAR" | grep "game/GAME" | head -5
echo ""

# settlement.main.SETT
echo "--- settlement.main.SETT ---"
jar tf "$JAR" | grep "settlement/main/SETT" | head -5
echo ""

# settlement.stats.STATS
echo "--- settlement.stats.STATS ---"
jar tf "$JAR" | grep "settlement/stats/STATS" | head -5
echo ""

# script.SCRIPT interface
echo "--- script.SCRIPT ---"
jar tf "$JAR" | grep "script/SCRIPT" | head -5
echo ""

echo "=== Decompiling key classes with javap ==="
echo ""

TMPDIR=$(mktemp -d)
cd "$TMPDIR"
jar xf "$JAR" 2>/dev/null

for CLASS in game.GAME settlement.main.SETT settlement.stats.STATS settlement.stats.standing.STANDINGS game.faction.FACTIONS settlement.room.main.Rooms; do
    FILE=$(echo "$CLASS" | tr '.' '/')".class"
    if [ -f "$FILE" ]; then
        echo "--- $CLASS ---"
        javap -p "$FILE" 2>/dev/null | head -60
        echo ""
    else
        echo "--- $CLASS: NOT FOUND ---"
        echo ""
    fi
done

# Also check the SCRIPT interface
SCRIPT_FILE="script/SCRIPT.class"
if [ -f "$SCRIPT_FILE" ]; then
    echo "--- script.SCRIPT interface ---"
    javap -p "$SCRIPT_FILE" 2>/dev/null
    echo ""
fi

cd - > /dev/null
rm -rf "$TMPDIR"

echo "=== Done ==="
