package syx.llm.overlord;

import game.GAME;
import game.GameSpeed;
import game.faction.FACTIONS;
import game.faction.player.Player;
import game.time.TIME;
import init.resources.RESOURCE;
import init.resources.RESOURCES;
import init.race.Race;
import settlement.army.ArmyManager;
import settlement.army.div.Div;
import settlement.main.SETT;
import settlement.room.main.ROOMS;
import settlement.room.main.RoomBlueprintImp;
import settlement.room.main.RoomBlueprintIns;
import settlement.room.main.throne.THRONE;
import settlement.stats.STATS;
import settlement.stats.colls.StatsPopulation;
import settlement.stats.standing.STANDINGS;
import settlement.stats.standing.StandingCitizen;
import util.data.INT;

import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;

/**
 * Reads game state using only primitive extractions safe for JSON export.
 */
public class StateReader {

    public GameState readState() {
        GameState state = new GameState();
        state.timestamp = System.currentTimeMillis();

        readGameTime(state);
        readGameSpeed(state);
        readThrone(state);
        readMapGrid(state);
        readPopulation(state);
        readHappiness(state);
        readResources(state);
        readMilitary(state);
        readRooms(state);
        readConstruction(state);
        readFactions(state);

        return state;
    }

    private void readGameTime(GameState state) {
        try {
            Map<String, Integer> time = new LinkedHashMap<>();
            time.put("day", TIME.days().bitCurrent());
            time.put("year", TIME.years().bitCurrent());
            time.put("hour", TIME.hours().bitCurrent());
            state.gameTime = time;
        } catch (Exception e) {
            state.errors.add("gameTime: " + e.getMessage());
        }
    }

    private void readGameSpeed(GameState state) {
        try {
            GameSpeed speed = GAME.SPEED;
            Map<String, Double> speedMap = new LinkedHashMap<>();
            speedMap.put("target", speed.speedTarget());
            speedMap.put("actual", speed.speed());
            speedMap.put("paused", speed.isPaused() ? 1.0 : 0.0);
            state.gameSpeed = speedMap;
        } catch (Exception e) {
            state.errors.add("gameSpeed: " + e.getMessage());
        }
    }

    private void readThrone(GameState state) {
        try {
            Map<String, Integer> throne = new LinkedHashMap<>();
            throne.put("x", THRONE.coo().x());
            throne.put("y", THRONE.coo().y());
            state.throne = throne;
        } catch (Exception e) {
            state.errors.add("throne: " + e.getMessage());
        }
    }

    private void readMapGrid(GameState state) {
        try {
            MapExporter.exportTo(state);
        } catch (Exception e) {
            state.errors.add("mapGrid: " + e.getMessage());
        }
    }

    private void readPopulation(GameState state) {
        try {
            StatsPopulation pop = STATS.POP();
            if (pop == null) {
                return;
            }
            Map<String, Integer> popMap = new LinkedHashMap<>();
            popMap.put("total", intValue(pop.POP.data().get(null)));
            state.population = popMap;
        } catch (Exception e) {
            state.errors.add("population: " + e.getMessage());
        }
    }

    private void readHappiness(GameState state) {
        try {
            StandingCitizen citizen = STANDINGS.CITIZEN();
            if (citizen == null) {
                return;
            }

            Race playerRace = GAME.player() != null ? GAME.player().race() : null;
            Map<String, Double> happyMap = new LinkedHashMap<>();
            happyMap.put("happiness", round(citizen.happiness.getD(playerRace)));
            happyMap.put("loyalty", round(citizen.loyalty.getD(playerRace)));
            happyMap.put("fulfillment", round(citizen.fullfillment.getD(playerRace)));
            happyMap.put("expectation", round(citizen.expectation.getD(playerRace)));
            happyMap.put("current", round(citizen.current()));
            happyMap.put("target", round(citizen.target()));
            happyMap.put("overall", round(citizen.current()));
            state.happiness = happyMap;
        } catch (Exception e) {
            state.errors.add("happiness: " + e.getMessage());
        }
    }

    private void readResources(GameState state) {
        try {
            Player player = GAME.player();
            if (player == null) {
                return;
            }

            Map<String, Integer> resMap = new LinkedHashMap<>();

            // Player.getAvailable() uses RESOURCE.sellable() (= stockpile+hauler only).
            // Without a stockpile that is always 0 even when farms exist — read the
            // stockpile tally directly, plus food sitting in canteens.
            try {
                var tally = SETT.ROOMS().STOCKPILE.tally();
                int listed = 0;
                for (RESOURCE r : RESOURCES.ALL()) {
                    int am = tally.amountTotal(r);
                    if (am > 0) {
                        resMap.put(r.key, am);
                        listed++;
                        if (listed >= 40) {
                            break;
                        }
                    }
                }
            } catch (Exception ignored) {
            }

            try {
                long canteenFood = 0;
                for (int i = 0; i < SETT.ROOMS().CANTEENS.size(); i++) {
                    canteenFood += SETT.ROOMS().CANTEENS.get(i).totalFood();
                }
                if (canteenFood > 0) {
                    resMap.put("canteen_food", (int) Math.min(canteenFood, Integer.MAX_VALUE));
                }
            } catch (Exception ignored) {
            }

            try {
                // Days of food buffer (stockpile + canteen/eatery). 0 is normal
                // before first harvest AND before any stockpile exists.
                int foodDays = STATS.FOOD().FOOD_DAYS.data().get(null);
                resMap.put("food_days", foodDays);
            } catch (Exception ignored) {
            }

            try {
                resMap.put("credits", (int) player.credits().credits());
            } catch (Exception ignored) {
            }

            // Always include crates so the LLM can see the chicken/egg.
            try {
                resMap.put("stockpile_crates", SETT.ROOMS().STOCKPILE.crates());
            } catch (Exception ignored) {
            }

            state.resources = resMap;
        } catch (Exception e) {
            state.errors.add("resources: " + e.getMessage());
        }
    }

    private void readMilitary(GameState state) {
        try {
            ArmyManager army = SETT.ARMIES();
            if (army == null) {
                return;
            }

            Map<String, Integer> milMap = new LinkedHashMap<>();
            snake2d.util.sets.LIST<Div> divisions = army.divisions();
            milMap.put("divisions", divisions.size());

            int totalMen = 0;
            for (int i = 0; i < divisions.size(); i++) {
                totalMen += divisions.get(i).menNrOf();
            }
            milMap.put("total_soldiers", totalMen);
            state.military = milMap;
        } catch (Exception e) {
            state.errors.add("military: " + e.getMessage());
        }
    }

    private void readRooms(GameState state) {
        try {
            ROOMS rooms = SETT.ROOMS();
            if (rooms == null) {
                return;
            }

            Map<String, Integer> roomMap = new LinkedHashMap<>();
            roomMap.put("stockpile_crates", rooms.STOCKPILE.crates());

            // HOME is RoomBlueprintImp (not Ins) — beds live on ROOM_HOME.total(HGROUP).
            int homeBeds = 0;
            try {
                if (rooms.HOME != null) {
                    for (init.type.HGROUP g : init.type.HGROUP.all()) {
                        homeBeds += rooms.HOME.total(g);
                    }
                }
            } catch (Exception ignored) {
            }

            int homeCount = 0;
            int farmCount = 0;
            int wellCount = 0;
            int hearthCount = 0;
            int canteenCount = 0;
            for (RoomBlueprintImp imp : rooms.imps()) {
                if (!(imp instanceof RoomBlueprintIns<?> ins)) {
                    continue;
                }
                int n = ins.instancesSize();
                if (n <= 0) {
                    continue;
                }
                String key = imp.key.toUpperCase(Locale.ROOT);
                if (key.contains("HOME") || key.equals("HOUSING")) {
                    homeCount += n;
                } else if (key.contains("WELL")) {
                    wellCount += n;
                } else if (key.contains("HEARTH")) {
                    hearthCount += n;
                } else if (key.contains("CANTEEN")) {
                    canteenCount += n;
                } else if (key.contains("FARM") && !key.contains("COTTON") && !key.contains("FLAX")) {
                    farmCount += n;
                }
            }
            // Prefer bed capacity from ROOM_HOME; fall back to Ins count if any.
            int homesReported = homeBeds > 0 ? homeBeds : homeCount;
            if (homesReported > 0) {
                roomMap.put("home", homesReported);
            }
            if (farmCount > 0) {
                roomMap.put("farm", farmCount);
            }
            if (wellCount > 0) {
                roomMap.put("well", wellCount);
            }
            if (hearthCount > 0) {
                roomMap.put("hearth", hearthCount);
            }
            if (canteenCount > 0) {
                roomMap.put("canteen", canteenCount);
            }

            state.roomCounts = roomMap;
        } catch (Exception e) {
            state.errors.add("rooms: " + e.getMessage());
        }
    }

    private void readConstruction(GameState state) {
        try {
            ROOMS rooms = SETT.ROOMS();
            if (rooms == null || rooms.construction == null) {
                return;
            }
            Map<String, Integer> conMap = new LinkedHashMap<>();
            conMap.put("instances", rooms.construction.instances());
            conMap.put("area", rooms.construction.area(false));
            state.construction = conMap;
        } catch (Exception e) {
            state.errors.add("construction: " + e.getMessage());
        }
    }

    private void readFactions(GameState state) {
        try {
            Map<String, String> dipMap = new LinkedHashMap<>();
            Player player = GAME.player();
            if (player != null) {
                dipMap.put("ruler", player.rulerName().toString());
                dipMap.put("race", player.race().key);
                dipMap.put("level", String.valueOf(player.level()));
            }
            dipMap.put("active_factions", String.valueOf(FACTIONS.active().size()));
            state.diplomacy = dipMap;
        } catch (Exception e) {
            state.errors.add("diplomacy: " + e.getMessage());
        }
    }

    private static int intValue(Object value) {
        if (value instanceof INT) {
            return ((INT) value).get();
        }
        if (value instanceof Number) {
            return ((Number) value).intValue();
        }
        return 0;
    }

    private static double round(Object val) {
        if (val instanceof Number) {
            return Math.round(((Number) val).doubleValue() * 1000.0) / 1000.0;
        }
        return 0.0;
    }
}
