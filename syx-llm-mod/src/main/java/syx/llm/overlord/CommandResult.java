package syx.llm.overlord;

/**
 * Result of executing a command.
 */
public class CommandResult {
    public boolean success;
    public String message;

    public CommandResult(boolean success, String message) {
        this.success = success;
        this.message = message;
    }
}
