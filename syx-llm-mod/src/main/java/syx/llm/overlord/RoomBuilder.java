package syx.llm.overlord;

import settlement.main.SETT;
import settlement.room.main.RoomBlueprintImp;
import settlement.room.main.furnisher.Furnisher;
import settlement.room.main.furnisher.FurnisherItemGroup;
import settlement.room.main.placement.RoomPlacer;
import settlement.room.main.throne.THRONE;
import snake2d.util.datatypes.AREA;
import snake2d.util.datatypes.COORDINATE;
import snake2d.util.datatypes.RECTANGLE;
import snake2d.util.datatypes.Rec;
import view.tool.PLACER_TYPE;
import view.tool.PlacableFixed;
import view.tool.PlacableMulti;

final class RoomBuilder {

    private static final int SEARCH_RADIUS = 40;
    private static final int ITEM_SEARCH_RADIUS = 20;
    private static final int DEFAULT_AREA = 4;

    private RoomBuilder() {
    }

    static CommandResult build(String target, int x, int y, java.util.Map<String, Object> params) {
        if (!SETT.IN_BOUNDS(x, y)) {
            return new CommandResult(false, "Coordinates out of bounds: (" + x + "," + y + ")");
        }

        // Release stale TmpArea lock left by interrupted placement (crashes game updater).
        releasePlacementState();

        RoomBlueprintImp blueprint = RoomResolver.resolve(target);
        if (blueprint == null) {
            return new CommandResult(false, "Unknown room type: " + target);
        }
        if (blueprint.constructor() == null) {
            return new CommandResult(false, "Room has no constructor: " + blueprint.key);
        }

        int itemGroup = intParam(params, "group", 0);
        int width = Math.max(1, intParam(params, "width", DEFAULT_AREA));
        int height = Math.max(1, intParam(params, "height", DEFAULT_AREA));
        // Canteen ovens+tables need >4x4, but 8x8 in forest creates a huge clear
        // backlog that starves the colony before builders finish. Cap at 6x6.
        if (blueprint.constructor() != null && blueprint.constructor().usesArea()
            && blueprint.key != null && blueprint.key.toUpperCase().contains("CANTEEN")) {
            if (params == null || !params.containsKey("width")) {
                width = 6;
            }
            if (params == null || !params.containsKey("height")) {
                height = 6;
            }
            width = Math.min(width, 6);
            height = Math.min(height, 6);
        }
        // Hard cap early area rooms — forest claims multiply clear jobs by tiles.
        if (blueprint.constructor() != null && blueprint.constructor().usesArea()) {
            width = Math.min(width, 8);
            height = Math.min(height, 8);
        }

        CommandResult direct = tryBuild(blueprint, x, y, itemGroup, width, height);
        if (direct.success) {
            return direct;
        }

        // Single-tile rooms (well, etc.): limited spiral with cleanup between attempts.
        if (!blueprint.constructor().usesArea()) {
            COORDINATE center = THRONE.coo();
            for (int radius = 1; radius <= ITEM_SEARCH_RADIUS; radius++) {
                for (int dy = -radius; dy <= radius; dy++) {
                    for (int dx = -radius; dx <= radius; dx++) {
                        if (Math.abs(dx) != radius && Math.abs(dy) != radius) {
                            continue;
                        }
                        int tx = center.x() + dx;
                        int ty = center.y() + dy;
                        if (tx == x && ty == y) {
                            continue;
                        }
                        CommandResult attempt = tryBuild(blueprint, tx, ty, itemGroup, width, height);
                        if (attempt.success) {
                            return new CommandResult(
                                true,
                                attempt.message + " (relocated from " + x + "," + y + ")"
                            );
                        }
                    }
                }
            }
            return new CommandResult(
                false,
                direct.message + " (also searched " + ITEM_SEARCH_RADIUS + " tiles around throne)"
            );
        }

        COORDINATE center = THRONE.coo();
        for (int radius = 1; radius <= SEARCH_RADIUS; radius++) {
            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    if (Math.abs(dx) != radius && Math.abs(dy) != radius) {
                        continue;
                    }
                    int tx = center.x() + dx;
                    int ty = center.y() + dy;
                    if (tx == x && ty == y) {
                        continue;
                    }
                    CommandResult attempt = tryBuild(blueprint, tx, ty, itemGroup, width, height);
                    if (attempt.success) {
                        return new CommandResult(true, attempt.message + " (relocated from " + x + "," + y + ")");
                    }
                }
            }
        }

        return new CommandResult(false, direct.message + " (also searched " + SEARCH_RADIUS + " tiles around throne)");
    }

    /** Clear TmpArea + placer embryo so the game updater does not crash on "In use by: PlacerItemSingle". */
    private static void releasePlacementState() {
        PlacementCleanup.release();
    }

    private static CommandResult tryBuild(
        RoomBlueprintImp blueprint,
        int x,
        int y,
        int itemGroup,
        int width,
        int height
    ) {
        if (!SETT.IN_BOUNDS(x, y)) {
            return new CommandResult(false, "Out of bounds: (" + x + "," + y + ")");
        }

        Furnisher constructor = blueprint.constructor();
        RoomPlacer placer = SETT.ROOMS().placement.placer;
        try {
            placer.init(blueprint, 0);

            if (constructor.usesArea()) {
                return buildArea(placer, blueprint, x, y, width, height);
            }
            return buildItem(placer, blueprint, x, y, itemGroup);
        } catch (Exception e) {
            return new CommandResult(false, blueprint.key + " error at (" + x + "," + y + "): " + e.getMessage());
        } finally {
            releasePlacementState();
        }
    }

    private static CommandResult buildItem(
        RoomPlacer placer,
        RoomBlueprintImp blueprint,
        int x,
        int y,
        int itemGroup
    ) {
        if (itemGroup >= blueprint.constructor().pgroups().size()) {
            return new CommandResult(false, "Item group " + itemGroup + " invalid for " + blueprint.key);
        }

        PlacableFixed itemPlacer = placer.item(itemGroup);
        CharSequence problem = itemPlacer.placableWhole(x, y);
        if (problem != null) {
            return new CommandResult(false, blueprint.key + " not placeable at (" + x + "," + y + "): " + problem);
        }

        itemPlacer.place(x, y, 0, 0);
        return new CommandResult(true, "Built " + blueprint.key + " at (" + x + "," + y + ")");
    }

    private static CommandResult buildArea(
        RoomPlacer placer,
        RoomBlueprintImp blueprint,
        int x,
        int y,
        int width,
        int height
    ) {
        RectArea area = new RectArea(x, y, width, height);
        PlacableMulti areaPlacer = (PlacableMulti) placer.area();

        for (int ty = area.body().y1(); ty < area.body().y2(); ty++) {
            for (int tx = area.body().x1(); tx < area.body().x2(); tx++) {
                CharSequence tileProblem = areaPlacer.isPlacable(tx, ty, area, PLACER_TYPE.SQUARE);
                if (tileProblem != null) {
                    return new CommandResult(false, blueprint.key + " area blocked at (" + tx + "," + ty + "): " + tileProblem);
                }
            }
        }

        for (int ty = area.body().y1(); ty < area.body().y2(); ty++) {
            for (int tx = area.body().x1(); tx < area.body().x2(); tx++) {
                areaPlacer.place(tx, ty, area, PLACER_TYPE.SQUARE);
            }
        }

        // Area rooms (canteen, …) require furniture + doorways before create().
        CommandResult items = placeRequiredItems(placer, blueprint, area);
        if (!items.success) {
            placer.init(null, 0);
            return items;
        }

        CommandResult doors = placeDoorways(placer, area);
        if (!doors.success) {
            placer.init(null, 0);
            return doors;
        }

        placer.setUpgrade(0);
        CharSequence createProblem = placer.createProblem();
        if (createProblem != null) {
            placer.init(null, 0);
            return new CommandResult(false, blueprint.key + " create blocked: " + createProblem
                + " [" + items.message + "; " + doors.message + "]");
        }

        CharSequence warning = placer.createWarning();
        placer.create();
        String message = "Built " + blueprint.key + " area " + width + "x" + height + " at (" + x + "," + y + ")";
        if (warning != null) {
            message += " (warning: " + warning + ")";
        }
        message += " (" + items.message + "; " + doors.message + ")";
        return new CommandResult(true, message);
    }

    /**
     * Keep placing the item group createProblem says is missing until create()
     * would succeed on items, or we can't place any more. Tries every size/rotation.
     */
    private static CommandResult placeRequiredItems(
        RoomPlacer placer,
        RoomBlueprintImp blueprint,
        RectArea area
    ) {
        Furnisher constructor = blueprint.constructor();
        if (constructor == null) {
            return new CommandResult(true, "no constructor");
        }
        int x1 = area.body().x1();
        int y1 = area.body().y1();
        int x2 = area.body().x2();
        int y2 = area.body().y2();
        StringBuilder diag = new StringBuilder();
        int totalPlaced = 0;

        for (int attempt = 0; attempt < 24; attempt++) {
            CharSequence problem = placer.createProblem();
            if (problem == null) {
                return new CommandResult(true, "items=" + totalPlaced + diag);
            }
            FurnisherItemGroup missing = placer.createProblemItem();
            if (missing == null) {
                // Walls/doorways/stats — handled by placeDoorways / createProblem next.
                return new CommandResult(true, "items=" + totalPlaced + diag);
            }
            int gi = missing.index();
            PlacableFixed itemPlacer = placer.item(gi);
            boolean placedOne = false;
            String lastFail = null;
            int sizes = Math.max(1, itemPlacer.sizes());
            int rots = Math.max(1, itemPlacer.rotations());
            outer:
            for (int sz = 0; sz < sizes && !placedOne; sz++) {
                itemPlacer.sizeSet(sz);
                for (int rt = 0; rt < rots && !placedOne; rt++) {
                    itemPlacer.rotSet(rt);
                    for (int ty = y1; ty < y2 && !placedOne; ty++) {
                        for (int tx = x1; tx < x2 && !placedOne; tx++) {
                            CharSequence tileProblem = itemPlacer.placableWhole(tx, ty);
                            if (tileProblem != null) {
                                lastFail = tileProblem.toString();
                                continue;
                            }
                            itemPlacer.place(tx, ty, 0, 0);
                            placedOne = true;
                            totalPlaced++;
                            diag.append(" | ").append(missing.name()).append("@").append(tx).append(',').append(ty)
                                .append(" s").append(sz).append("r").append(rt);
                            break outer;
                        }
                    }
                }
            }
            if (!placedOne) {
                return new CommandResult(
                    false,
                    blueprint.key + " need '" + missing.name() + "' but no placable tile in "
                        + area.body().width() + "x" + area.body().height()
                        + (lastFail != null ? " (last: " + lastFail + ")" : "")
                        + diag
                );
            }
            // UtilStats caches per GAME.updateI() — bust so createProblem sees new items.
            placer.setUpgrade(0);
        }
        return new CommandResult(
            false,
            blueprint.key + " still blocked after item placement attempts" + diag
        );
    }

    /** Place wall openings so indoor rooms are reachable from outside. */
    private static CommandResult placeDoorways(RoomPlacer placer, RectArea area) {
        placer.autoWalls.set(true);
        PlacableMulti doorPlacer = placer.placerDoor;
        int x1 = area.body().x1() - 1;
        int y1 = area.body().y1() - 1;
        int x2 = area.body().x2() + 1;
        int y2 = area.body().y2() + 1;
        int placed = 0;
        String lastFail = null;

        for (int attempt = 0; attempt < 16; attempt++) {
            placer.setUpgrade(0);
            CharSequence problem = placer.createProblem();
            if (problem == null) {
                return new CommandResult(true, "doors=" + placed);
            }
            // Still missing furniture — don't treat as doorway failure.
            if (placer.createProblemItem() != null) {
                return new CommandResult(true, "doors=" + placed + " (items still needed)");
            }

            boolean placedOne = false;
            for (int ty = y1; ty < y2 && !placedOne; ty++) {
                for (int tx = x1; tx < x2 && !placedOne; tx++) {
                    CharSequence tileProblem = doorPlacer.isPlacable(tx, ty, area, PLACER_TYPE.SQUARE);
                    if (tileProblem != null) {
                        lastFail = tileProblem.toString();
                        continue;
                    }
                    doorPlacer.place(tx, ty, area, PLACER_TYPE.SQUARE);
                    placed++;
                    placedOne = true;
                }
            }
            if (!placedOne) {
                return new CommandResult(
                    false,
                    "need doorway but none placable"
                        + (lastFail != null ? " (last: " + lastFail + ")" : "")
                        + " — " + problem
                );
            }
        }
        return new CommandResult(false, "still blocked after doorway attempts (doors=" + placed + ")");
    }

    private static int intParam(java.util.Map<String, Object> params, String key, int defaultValue) {
        if (params == null || !params.containsKey(key)) {
            return defaultValue;
        }
        Object raw = params.get(key);
        if (raw instanceof Number number) {
            return number.intValue();
        }
        return defaultValue;
    }

    private static final class RectArea implements AREA {
        private final Rec body;

        RectArea(int x, int y, int width, int height) {
            body = new Rec().setDim(width, height).moveX1Y1(x, y);
        }

        @Override
        public RECTANGLE body() {
            return body;
        }

        @Override
        public boolean is(int tile) {
            int tx = tile % SETT.TWIDTH;
            int ty = tile / SETT.TWIDTH;
            return is(tx, ty);
        }

        @Override
        public boolean is(int tx, int ty) {
            return body.holdsPoint(tx, ty);
        }

        @Override
        public int area() {
            return body.width() * body.height();
        }
    }
}
