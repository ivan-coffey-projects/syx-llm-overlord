package syx.llm.overlord;

import settlement.main.SETT;
import settlement.room.main.Room;
import settlement.room.main.construction.CONSTRUCTION;
import settlement.room.main.throne.THRONE;
import snake2d.util.datatypes.COORDINATE;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/**
 * Escape hatch for unattended play: instant-finish or cancel construction
 * sites stuck on forest-clear jobs.
 *
 * Scans via public {@link CONSTRUCTION#isser} + {@link Room#mX}/{@link Room#mY}
 * — avoids reflecting into package-private ConstructionInstance (Java denies that).
 */
final class ConstructionRescue {

    private static final int SCAN_RADIUS = 80;

    private ConstructionRescue() {
    }

    static CommandResult finishAll() {
        try {
            List<int[]> sites = listMasterTiles();
            if (sites.isEmpty()) {
                return new CommandResult(true, "No construction sites to finish");
            }
            CONSTRUCTION con = SETT.ROOMS().construction;
            int n = 0;
            for (int[] xy : sites) {
                try {
                    con.construct(xy[0], xy[1]);
                    n++;
                } catch (Exception ignored) {
                }
            }
            return new CommandResult(true, "Finished " + n + "/" + sites.size() + " construction site(s)");
        } catch (Exception e) {
            return new CommandResult(false, "finish_construction failed: " + e.getMessage());
        }
    }

    static CommandResult cancelAll() {
        try {
            List<int[]> sites = listMasterTiles();
            if (sites.isEmpty()) {
                return new CommandResult(true, "No construction sites to cancel");
            }
            int n = 0;
            for (int[] xy : sites) {
                try {
                    Room r = SETT.ROOMS().map.get(xy[0], xy[1]);
                    if (r == null) {
                        continue;
                    }
                    r.remove(xy[0], xy[1], false, ConstructionRescue.class, true);
                    n++;
                } catch (Exception ignored) {
                }
            }
            return new CommandResult(true, "Cancelled " + n + "/" + sites.size() + " construction site(s)");
        } catch (Exception e) {
            return new CommandResult(false, "cancel_construction failed: " + e.getMessage());
        }
    }

    /** Unique master tiles of every open construction instance near the throne. */
    private static List<int[]> listMasterTiles() {
        CONSTRUCTION con = SETT.ROOMS().construction;
        if (con == null || con.instances() <= 0) {
            return List.of();
        }
        COORDINATE throne = THRONE.coo();
        int cx = throne.x();
        int cy = throne.y();
        Set<Long> seen = new LinkedHashSet<>();
        List<int[]> out = new ArrayList<>();

        for (int dy = -SCAN_RADIUS; dy <= SCAN_RADIUS; dy++) {
            for (int dx = -SCAN_RADIUS; dx <= SCAN_RADIUS; dx++) {
                int x = cx + dx;
                int y = cy + dy;
                if (!SETT.IN_BOUNDS(x, y) || !con.isser.is(x, y)) {
                    continue;
                }
                Room r = SETT.ROOMS().map.get(x, y);
                if (r == null) {
                    continue;
                }
                int mx = r.mX(x, y);
                int my = r.mY(x, y);
                long key = (((long) mx) << 32) ^ (my & 0xffffffffL);
                if (!seen.add(key)) {
                    continue;
                }
                out.add(new int[]{mx, my});
            }
        }
        return out;
    }
}
