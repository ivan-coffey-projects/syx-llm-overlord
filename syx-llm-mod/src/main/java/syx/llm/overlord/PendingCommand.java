package syx.llm.overlord;

import java.util.concurrent.CompletableFuture;

final class PendingCommand {
    final Command command;
    final CompletableFuture<CommandResult> result = new CompletableFuture<>();

    PendingCommand(Command command) {
        this.command = command;
    }
}
