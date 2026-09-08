package syx.llm.overlord;

import game.GAME;
import game.faction.player.Player;

/**
 * "No-die" cheat for unattended / streamed play.
 *
 * Applies large, persistent survival bonuses to the player's subjects through
 * the game's OWN bonus system ({@code Player.bonusesCustom}, a PBonusSetting).
 * That path is engine-sanctioned and recomputed by the boosting system, so it
 * cannot corrupt stockpile/crate state or crash the settlement the way poking
 * resource internals would.
 *
 * Subjects become extremely happy, healthy, long-lived, weather-proof, loyal
 * and sane — and hunger/thirst gain is nearly stopped so a colony left on
 * autopilot does not starve while the LLM catches up on canteen/farm builds.
 *
 * Enabled by env var {@code SYX_NO_DIE=1} (set on the game's launch env).
 */
final class NoDieCheat {

    private static final boolean ENABLED =
            "1".equals(System.getenv("SYX_NO_DIE"))
                    || "true".equalsIgnoreCase(System.getenv("SYX_NO_DIE"));

    /**
     * boostable key -> factor, isMul.
     * More-is-better stats use mul &gt; 1. Need rates (hunger/thirst) use mul ≪ 1
     * so daily need gain collapses (PBonusSetting rejects mul==1 and value==0).
     */
    private static final Object[][] BOOSTS = {
            // Behaviour / physics — more is better
            {"HAPPINESS", 25.0, true},
            {"HEALTH", 25.0, true},
            {"DEATH_AGE", 10.0, true},       // ~1000-year lifespan -> no aging deaths
            {"RESISTANCE_COLD", 25.0, true}, // survive winter
            {"RESISTANCE_HOT", 25.0, true},
            {"SANITY", 25.0, true},
            {"LOYALTY", 25.0, true},
            {"SUBMISSION", 25.0, true},
            // Need rates — key == need id from data/assets/init/stats/need/_HUNGER.txt
            // RATE boostable is registered under the need key (_HUNGER / _THIRST).
            {"_HUNGER", 0.001, true},        // 0.1% hunger gain — year-safe without canteen
            {"_THIRST", 0.001, true},        // 0.1% thirst gain
            {"SPOILAGE", 25.0, true},        // Conservation — food lasts
            // IMMIGRATION removed: a x25 pull the moment a home exists yanks a huge
            // immigrant wave into a half-built 4x4 home and crashes the sim, which
            // auto-reloads the last autosave and wipes the home (so pop never grew).
            // HAPPINESS x25 above still attracts immigrants at a sane rate.
    };

    private boolean applied = false;

    boolean enabled() {
        return ENABLED;
    }

    /** Allow re-apply after save load / new settlement (bonuses may have reset). */
    void reset() {
        applied = false;
    }

    /**
     * Apply the survival boosts once, after the player exists. Cheap and
     * self-guarding: safe to call every tick, no-ops after it succeeds.
     */
    void applyOnce() {
        if (applied || !ENABLED) {
            return;
        }
        try {
            Player p = GAME.player();
            if (p == null || p.bonusesCustom == null) {
                return; // settlement not ready yet — retry next tick
            }
            int n = 0;
            for (Object[] b : BOOSTS) {
                try {
                    String key = (String) b[0];
                    double factor = (Double) b[1];
                    boolean isMul = (Boolean) b[2];
                    p.bonusesCustom.add(key, factor, isMul);
                    n++;
                } catch (Exception ignored) {
                    // a single bad/renamed key must not abort the rest
                }
            }
            applied = true;
            System.out.println("[LLM Overlord] NO-DIE cheat applied (" + n + " survival boosts, hunger/thirst near-zero)");
        } catch (Exception e) {
            System.err.println("[LLM Overlord] NO-DIE apply failed: " + e.getMessage());
        }
    }
}
