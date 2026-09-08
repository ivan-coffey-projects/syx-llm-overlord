package syx.llm.overlord;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Snapshot of game state, serialized to JSON for the LLM bridge.
 * Values must be JSON primitives only — never store game engine objects here.
 *
 * Serialization is done by hand in toJson() so Gson never walks a game object
 * graph reflectively (the Gson path could recurse into an engine object and
 * exhaust the heap). Manual building keeps output bounded and crash-free.
 */
public class GameState {
    public long timestamp;
    public int tickCount;
    public Map<String, Integer> population = new LinkedHashMap<>();
    public Map<String, Integer> resources = new LinkedHashMap<>();
    public Map<String, Double> happiness = new LinkedHashMap<>();
    public Map<String, Integer> roomCounts = new LinkedHashMap<>();
    public Map<String, Integer> construction = new LinkedHashMap<>();
    public Map<String, Integer> military = new LinkedHashMap<>();
    public Map<String, String> diplomacy = new LinkedHashMap<>();
    public Map<String, Integer> gameTime = new LinkedHashMap<>();
    public Map<String, Double> gameSpeed = new LinkedHashMap<>();
    public Map<String, Integer> throne = new LinkedHashMap<>();
    public int mapCenterX;
    public int mapCenterY;
    public int mapRadius;
    public boolean mapFull;
    public int mapX1;
    public int mapY1;
    public int mapX2;
    public int mapY2;
    public String mapLegend = "";
    public List<String> mapRows = new ArrayList<>();
    public List<String> errors = new ArrayList<>();

    /** Build JSON directly from primitive maps. No reflection, no recursion, bounded. */
    public String toJson() {
        StringBuilder sb = new StringBuilder(2048);
        sb.append('{');
        sb.append("\"timestamp\":").append(timestamp).append(',');
        sb.append("\"tickCount\":").append(tickCount).append(',');
        appendIntMap(sb, "population", population);
        appendIntMap(sb, "resources", resources);
        appendDoubleMap(sb, "happiness", happiness);
        appendIntMap(sb, "roomCounts", roomCounts);
        appendIntMap(sb, "construction", construction);
        appendIntMap(sb, "military", military);
        appendStringMap(sb, "diplomacy", diplomacy);
        appendIntMap(sb, "gameTime", gameTime);
        appendDoubleMap(sb, "gameSpeed", gameSpeed);
        appendIntMap(sb, "throne", throne);
        sb.append("\"mapCenterX\":").append(mapCenterX).append(',');
        sb.append("\"mapCenterY\":").append(mapCenterY).append(',');
        sb.append("\"mapRadius\":").append(mapRadius).append(',');
        sb.append("\"mapFull\":").append(mapFull).append(',');
        sb.append("\"mapX1\":").append(mapX1).append(',');
        sb.append("\"mapY1\":").append(mapY1).append(',');
        sb.append("\"mapX2\":").append(mapX2).append(',');
        sb.append("\"mapY2\":").append(mapY2).append(',');
        sb.append("\"mapLegend\":\"").append(escape(mapLegend)).append("\",");
        appendStringList(sb, "mapRows", mapRows);
        sb.append("\"errors\":[");
        for (int i = 0; i < errors.size(); i++) {
            if (i > 0) sb.append(',');
            sb.append('"').append(escape(errors.get(i))).append('"');
        }
        sb.append(']');
        sb.append('}');
        return sb.toString();
    }

    private void appendIntMap(StringBuilder sb, String name, Map<String, Integer> map) {
        sb.append('"').append(name).append("\":{");
        boolean first = true;
        for (Map.Entry<String, Integer> e : map.entrySet()) {
            if (!first) sb.append(',');
            first = false;
            sb.append('"').append(escape(e.getKey())).append("\":").append(num(e.getValue()));
        }
        sb.append("},");
    }

    private void appendDoubleMap(StringBuilder sb, String name, Map<String, Double> map) {
        sb.append('"').append(name).append("\":{");
        boolean first = true;
        for (Map.Entry<String, Double> e : map.entrySet()) {
            if (!first) sb.append(',');
            first = false;
            sb.append('"').append(escape(e.getKey())).append("\":").append(num(e.getValue()));
        }
        sb.append("},");
    }

    private void appendStringList(StringBuilder sb, String name, List<String> list) {
        sb.append('"').append(name).append("\":[");
        for (int i = 0; i < list.size(); i++) {
            if (i > 0) {
                sb.append(',');
            }
            sb.append('"').append(escape(list.get(i))).append('"');
        }
        sb.append("],");
    }

    private void appendStringMap(StringBuilder sb, String name, Map<String, String> map) {
        sb.append('"').append(name).append("\":{");
        boolean first = true;
        for (Map.Entry<String, String> e : map.entrySet()) {
            if (!first) sb.append(',');
            first = false;
            sb.append('"').append(escape(e.getKey())).append("\":\"").append(escape(e.getValue())).append('"');
        }
        sb.append("},");
    }

    private static String num(Object v) {
        if (v == null) return "0";
        if (v instanceof Number) return v.toString();
        return "0";
    }

    private static String escape(String s) {
        if (s == null) return "";
        StringBuilder out = new StringBuilder(s.length());
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"' -> out.append("\\\"");
                case '\\' -> out.append("\\\\");
                case '\n' -> out.append("\\n");
                case '\r' -> out.append("\\r");
                case '\t' -> out.append("\\t");
                default -> {
                    if (c < 0x20) {
                        out.append(String.format("\\u%04x", (int) c));
                    } else {
                        out.append(c);
                    }
                }
            }
        }
        return out.toString();
    }
}
