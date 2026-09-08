package syx.llm.overlord;

import settlement.main.SETT;

import java.lang.reflect.Field;

/** Clears TmpArea/placer locks via reflection (tmpArea is package-private on ROOMS). */
final class PlacementCleanup {

    private PlacementCleanup() {
    }

    static void release() {
        try {
            SETT.ROOMS().placement.placer.init(null, 0);
        } catch (Exception ignored) {
        }
        try {
            Field f = SETT.ROOMS().getClass().getDeclaredField("tmpArea");
            f.setAccessible(true);
            Object tmp = f.get(SETT.ROOMS());
            tmp.getClass().getMethod("clear").invoke(tmp);
        } catch (Exception ignored) {
        }
    }
}
