package syx.llm.overlord;

import settlement.main.SETT;
import settlement.room.main.ROOMS;
import settlement.room.main.RoomBlueprintImp;
import snake2d.util.sets.LIST;

import java.util.Locale;

final class RoomResolver {

    private RoomResolver() {
    }

    static RoomBlueprintImp resolve(String target) {
        if (target == null || target.isBlank()) {
            return null;
        }
        ROOMS rooms = SETT.ROOMS();
        if (rooms == null) {
            return null;
        }

        String normalized = target.trim().toLowerCase(Locale.ROOT)
            .replace(' ', '_')
            .replace('-', '_');

        RoomBlueprintImp direct = switch (normalized) {
            case "stockpile", "stockpile_crates", "crates", "granary" -> rooms.STOCKPILE;
            case "home", "housing", "house", "settler_tent", "tent", "shelter" -> rooms.HOME;
            case "well" -> first(rooms.WELLS);
            case "farm", "farm_grain", "grain", "food" -> resolveFoodFarm(rooms);
            case "farm_cotton", "cotton" -> findByKey(rooms, "COTTON");
            case "farm_veg", "veg", "vegetable" -> findByKey(rooms, "VEG");
            case "farm_herb", "herb" -> findByKey(rooms, "HERB");
            case "farm_mushroom", "mushroom" -> findByKey(rooms, "MUSHROOM");
            case "fishery", "fish" -> first(rooms.FISHERIES);
            case "hunter" -> first(rooms.HUNTERS);
            case "pasture" -> first(rooms.PASTURES);
            case "orchard" -> first(rooms.ORCHARDS);
            case "woodcutter", "wood_cutter" -> rooms.WOOD_CUTTER;
            case "mine" -> first(rooms.MINES);
            case "workshop" -> first(rooms.WORKSHOPS);
            case "builder" -> rooms.BUILDER;
            case "bench" -> rooms.BENCH;
            case "canteen", "eatery", "diner", "mess", "dining" -> findByKey(rooms, "CANTEEN");
            case "tavern" -> first(rooms.TAVERNS);
            case "market" -> first(rooms.MARKET);
            case "barracks" -> first(rooms.BARRACKS);
            case "inn" -> rooms.INN;
            case "export" -> rooms.EXPORT;
            case "import" -> rooms.IMPORT;
            case "hauler" -> rooms.HAULER;
            case "transport" -> rooms.TRANSPORT;
            case "station" -> rooms.STATION;
            case "janitor" -> rooms.JANITOR;
            case "hospital" -> rooms.HOSPITAL;
            case "guard" -> rooms.GUARD;
            case "prison" -> rooms.PRISON;
            case "court" -> rooms.COURT;
            case "hearth" -> rooms.HEARTH;
            case "cannibal" -> rooms.CANNIBAL;
            default -> null;
        };
        if (direct != null) {
            return direct;
        }

        String key = normalized.startsWith("_") ? normalized : "_" + normalized.toUpperCase(Locale.ROOT);
        for (RoomBlueprintImp blueprint : rooms.imps()) {
            if (blueprint.key.equalsIgnoreCase(key) || blueprint.key.equalsIgnoreCase(normalized)) {
                return blueprint;
            }
        }

        String needle = normalized.toUpperCase(Locale.ROOT);
        for (RoomBlueprintImp blueprint : rooms.imps()) {
            if (blueprint.key.toUpperCase(Locale.ROOT).contains(needle)) {
                return blueprint;
            }
        }
        return null;
    }

    private static RoomBlueprintImp first(LIST<?> list) {
        if (list == null || list.size() == 0) {
            return null;
        }
        Object value = list.get(0);
        return value instanceof RoomBlueprintImp blueprint ? blueprint : null;
    }

    /** Prefer grain/veg food farms — generic `farm` must not default to cotton/industry. */
    private static RoomBlueprintImp resolveFoodFarm(ROOMS rooms) {
        String[] prefer = {"GRAIN", "WHEAT", "VEG", "MUSHROOM", "HERB", "FRUIT"};
        for (String keyword : prefer) {
            RoomBlueprintImp bp = findByKey(rooms, keyword);
            if (bp != null && bp.key.contains("FARM")) {
                return bp;
            }
        }
        for (RoomBlueprintImp blueprint : rooms.imps()) {
            String key = blueprint.key.toUpperCase(Locale.ROOT);
            if (!key.contains("FARM")) {
                continue;
            }
            if (key.contains("COTTON") || key.contains("FLAX") || key.contains("INDUSTRY")) {
                continue;
            }
            return blueprint;
        }
        return first(rooms.FARMS);
    }

    private static RoomBlueprintImp findByKey(ROOMS rooms, String keyword) {
        String needle = keyword.toUpperCase(Locale.ROOT);
        for (RoomBlueprintImp blueprint : rooms.imps()) {
            if (blueprint.key.toUpperCase(Locale.ROOT).contains(needle)) {
                return blueprint;
            }
        }
        return null;
    }
}
