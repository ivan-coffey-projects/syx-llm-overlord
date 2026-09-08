package syx.llm.overlord;

import script.SCRIPT;
import script.SCRIPT.SCRIPT_INSTANCE;

/**
 * Songs of Syx mod that exposes game state via HTTP and accepts commands,
 * allowing an external LLM to observe and control the game.
 *
 * Implements SCRIPT interface: name(), desc(), createInstance()
 * The SCRIPT_INSTANCE gets the update(double) game loop hook.
 */
public class LlmOverlordScript implements SCRIPT {

    @Override
    public CharSequence name() {
        return "LLM Overlord";
    }

    @Override
    public CharSequence desc() {
        return "Lets an AI overlord observe and control your kingdom via HTTP API on port 47823.";
    }

    @Override
    public SCRIPT_INSTANCE createInstance() {
        return new LlmOverlordInstance();
    }

    @Override
    public boolean isSelectable() {
        return false;
    }

    @Override
    public boolean forceInit() {
        return true;
    }
}
