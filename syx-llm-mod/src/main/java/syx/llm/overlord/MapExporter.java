package syx.llm.overlord;

import settlement.main.SETT;
import settlement.room.main.RoomBlueprintImp;
import settlement.room.main.RoomInstance;
import settlement.room.main.throne.THRONE;
import settlement.tilemap.ground.GroundType;
import settlement.tilemap.terrain.Terrain;
import snake2d.util.datatypes.RECTANGLE;

import init.type.TERRAIN;

/**
 * Exports ASCII tile grid for the dashboard.
 * Uses expanded settlement bounds when large enough; otherwise a wide throne-centered view.
 * The bridge strips mapRows from LLM prompts unless map.llm_enabled is true.
 */
final class MapExporter {

    /** Dashboard view when WORLD_AREA is still tiny (early game). */
    static final int DISPLAY_RADIUS = 64;
    /** Minimum span before WORLD_AREA alone is used as the export window. */
    static final int MIN_WORLD_SPAN = 32;

    private MapExporter() {
    }

    static void exportTo(GameState state) {
        try {
            RECTANGLE world = SETT.WORLD_AREA().tiles();
            int w = world.x2() - world.x1() + 1;
            int h = world.y2() - world.y1() + 1;
            if (w >= MIN_WORLD_SPAN && h >= MIN_WORLD_SPAN) {
                exportBounds(state, world, "FULL settlement bounds");
            } else {
                int cx = THRONE.coo().x();
                int cy = THRONE.coo().y();
                exportThroneRadius(state, cx, cy, DISPLAY_RADIUS,
                    "Wide build preview (settlement not expanded yet — "
                        + w + "×" + h + " claimed; showing " + DISPLAY_RADIUS + " tiles from throne)");
            }
        } catch (Exception e) {
            state.errors.add("mapGrid: " + e.getMessage());
            exportThroneRadius(state, THRONE.coo().x(), THRONE.coo().y(), 20, "Legacy fallback");
        }
    }

    static void exportBounds(GameState state, RECTANGLE bounds, String label) {
        int x1 = bounds.x1();
        int x2 = bounds.x2();
        int y1 = bounds.y1();
        int y2 = bounds.y2();

        state.mapFull = true;
        state.mapX1 = x1;
        state.mapY1 = y1;
        state.mapX2 = x2;
        state.mapY2 = y2;
        state.mapCenterX = bounds.cX();
        state.mapCenterY = bounds.cY();
        int w = x2 - x1 + 1;
        int h = y2 - y1 + 1;
        state.mapRadius = Math.max(w, h) / 2;
        state.mapLegend =
            "T=throne +=room(building) .=open ~ =water ^=forest/tree M=mountain/cave X=blocked ?=unknown/outside. "
            + label + " (x1=" + x1 + ",y1=" + y1 + " → x2=" + x2 + ",y2=" + y2 + "). "
            + "Rows north→south; columns west→east.";

        fillRows(state, x1, y1, x2, y2);
    }

    static void exportThroneRadius(GameState state, int cx, int cy, int radius, String label) {
        radius = Math.max(5, radius);
        state.mapFull = false;
        state.mapX1 = cx - radius;
        state.mapY1 = cy - radius;
        state.mapX2 = cx + radius;
        state.mapY2 = cy + radius;
        state.mapCenterX = cx;
        state.mapCenterY = cy;
        state.mapRadius = radius;
        state.mapLegend =
            "T=throne +=room .=open ~ =water ^=forest M=mountain X=blocked ?=unknown. "
            + label + ".";

        fillRows(state, state.mapX1, state.mapY1, state.mapX2, state.mapY2);
    }

    private static void fillRows(GameState state, int x1, int y1, int x2, int y2) {
        int tx = THRONE.coo().x();
        int ty = THRONE.coo().y();
        state.mapRows.clear();
        for (int y = y1; y <= y2; y++) {
            StringBuilder row = new StringBuilder(x2 - x1 + 1);
            for (int x = x1; x <= x2; x++) {
                row.append(classify(x, y, tx, ty));
            }
            state.mapRows.add(row.toString());
        }
    }

    private static char classify(int x, int y, int throneX, int throneY) {
        if (x == throneX && y == throneY) {
            return 'T';
        }
        if (!SETT.IN_BOUNDS(x, y)) {
            return '?';
        }

        try {
            RoomInstance instance = SETT.ROOMS().map.instance.get(x, y);
            if (instance != null) {
                RoomBlueprintImp blueprint = SETT.ROOMS().map.blueprintImp.get(x, y);
                if (blueprint != null && blueprint.key != null && !blueprint.key.isEmpty()) {
                    char c = Character.toUpperCase(blueprint.key.charAt(0));
                    if (Character.isLetterOrDigit(c)) {
                        return c;
                    }
                }
                return '+';
            }

            if (SETT.PLACA().willBlock.is(x, y) || SETT.PLACA().solidityWill.is(x, y)) {
                return 'X';
            }

            Terrain.TerrainTile tile = SETT.TERRAIN().get(x, y);
            if (tile != null) {
                TERRAIN terrain = tile.terrain(x, y);
                if (terrain != null) {
                    String key = terrain.key();
                    if (key != null) {
                        String k = key.toUpperCase();
                        if (k.contains("WATER") || k.contains("LAKE") || k.contains("RIVER")) {
                            return '~';
                        }
                        if (k.contains("MOUNT") || k.contains("CAVE") || k.contains("ROCK")) {
                            return 'M';
                        }
                    }
                }
            }

            GroundType ground = SETT.GROUND().MAP.get(x, y);
            if (ground != null) {
                if (ground.vegitation > 0.25) {
                    return '^';
                }
            }

            return '.';
        } catch (Exception e) {
            return '?';
        }
    }
}
