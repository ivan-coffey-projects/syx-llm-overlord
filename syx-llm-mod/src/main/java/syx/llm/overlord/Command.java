package syx.llm.overlord;

import java.util.Map;

/**
 * Command sent by the LLM to execute in-game actions.
 */
public class Command {
    public String action;
    public String target;
    public Integer x;
    public Integer y;
    public Map<String, Object> params;
}
