package syx.llm.overlord;

import com.google.gson.Gson;
import script.SCRIPT.SCRIPT_INSTANCE;
import snake2d.util.file.FileGetter;
import snake2d.util.file.FilePutter;

import java.io.IOException;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

/**
 * Mod instance: HTTP API + per-tick state snapshots.
 * Commands are queued from HTTP worker threads and executed on the game thread.
 */
public class LlmOverlordInstance implements SCRIPT_INSTANCE {

    private static final int PORT = 47823;
    private static final int MAX_STATE_BYTES = 256_000;
    private static final long COMMAND_TIMEOUT_MS = 10_000;
    /** One command per game tick; builds need spacing to avoid TmpArea / PlacerItemSingle crashes. */
    private static final int MAX_COMMANDS_PER_TICK = 1;
    /** ~5s at 60fps between blueprint placements (game thread update calls). */
    private static final int BUILD_COOLDOWN_TICKS = 300;
    private static final Gson GSON = new Gson();

    private int lastBuildTick = -999;

    private static volatile LlmOverlordInstance activeInstance;
    private static SimpleHttpServer sharedHttpServer;

    private final StateReader stateReader = new StateReader();
    private final CommandExecutor commandExecutor = new CommandExecutor();
    private final NoDieCheat noDie = new NoDieCheat();
    private final ConcurrentLinkedQueue<PendingCommand> commandQueue = new ConcurrentLinkedQueue<>();
    private volatile String lastStateJson = "{\"error\":\"warming up\"}";
    private int tickCount = 0;

    public LlmOverlordInstance() {
        activeInstance = this;
        ensureHttpServer();
    }

    private static synchronized void ensureHttpServer() {
        if (sharedHttpServer != null) {
            return;
        }
        try {
            LlmOverlordInstance bootstrap = activeInstance;
            sharedHttpServer = new SimpleHttpServer(PORT, 2);
            sharedHttpServer.route("/api/health", bootstrap::handleHealth);
            sharedHttpServer.route("/api/state", bootstrap::handleGetState);
            sharedHttpServer.route("/api/command", bootstrap::handlePostCommand);
            sharedHttpServer.start();
            System.out.println("[LLM Overlord] HTTP API running at http://localhost:" + PORT);
        } catch (IOException e) {
            System.err.println("[LLM Overlord] Failed to start HTTP server: " + e.getMessage());
        }
    }

    @Override
    public void update(double ds) {
        tickCount++;
        processPendingCommands();

        if (noDie.enabled()) {
            noDie.applyOnce();
        }

        if (tickCount != 1 && tickCount % 10 != 0) {
            return;
        }
        try {
            GameState state = stateReader.readState();
            state.tickCount = tickCount;
            String json = state.toJson();
            if (json.length() > MAX_STATE_BYTES) {
                json = "{\"error\":\"state too large\",\"tick\":" + tickCount + "}";
            }
            lastStateJson = json;
        } catch (OutOfMemoryError oom) {
            lastStateJson = "{\"error\":\"oom reading state\",\"tick\":" + tickCount + "}";
            System.err.println("[LLM Overlord] OOM reading state at tick " + tickCount);
        } catch (Exception e) {
            if (tickCount % 100 == 0) {
                System.err.println("[LLM Overlord] State read error: " + e.getMessage());
            }
        }
    }

    private void processPendingCommands() {
        int processed = 0;
        PendingCommand pending;
        while (processed < MAX_COMMANDS_PER_TICK && (pending = commandQueue.poll()) != null) {
            if ("build".equals(pending.command.action)
                    && tickCount - lastBuildTick < BUILD_COOLDOWN_TICKS) {
                pending.result.complete(new CommandResult(false,
                        "Build cooldown — wait a few seconds before next placement"));
                processed++;
                continue;
            }
            try {
                if ("build".equals(pending.command.action)) {
                    releaseStaleBuildState();
                }
                CommandResult result = commandExecutor.execute(pending.command);
                pending.result.complete(result);
                if ("build".equals(pending.command.action) && result.success) {
                    lastBuildTick = tickCount;
                }
                processed++;
            } catch (Exception e) {
                pending.result.complete(new CommandResult(false, "Error: " + e.getMessage()));
                processed++;
            } finally {
                if ("build".equals(pending.command.action)) {
                    releaseStaleBuildState();
                }
            }
        }
    }

    private static void releaseStaleBuildState() {
        PlacementCleanup.release();
    }

    @Override
    public void save(FilePutter file) {
        file.i(tickCount);
    }

    @Override
    public void load(FileGetter file) throws IOException {
        tickCount = file.i();
        activeInstance = this;
        noDie.reset();
    }

    private void handleHealth(SimpleHttpServer.Request request, SimpleHttpServer.Response response) {
        LlmOverlordInstance live = activeInstance;
        int tick = live != null ? live.tickCount : 0;
        response.json(200, "{\"status\":\"ok\",\"tick\":" + tick + "}");
    }

    private void handleGetState(SimpleHttpServer.Request request, SimpleHttpServer.Response response) {
        if (!"GET".equals(request.method)) {
            response.json(405, "{\"error\":\"Method not allowed\"}");
            return;
        }
        LlmOverlordInstance live = activeInstance;
        if (live == null || live.tickCount < 1) {
            response.json(503, "{\"error\":\"No state available yet, wait for first tick\"}");
            return;
        }
        response.json(200, live.lastStateJson);
    }

    private void handlePostCommand(SimpleHttpServer.Request request, SimpleHttpServer.Response response) {
        if (!"POST".equals(request.method)) {
            response.json(405, "{\"error\":\"Method not allowed\"}");
            return;
        }
        LlmOverlordInstance live = activeInstance;
        if (live == null) {
            response.json(503, "{\"error\":\"Game not loaded\"}");
            return;
        }
        try {
            Command cmd = GSON.fromJson(request.body, Command.class);
            PendingCommand pending = new PendingCommand(cmd);
            live.commandQueue.offer(pending);
            CommandResult result = pending.result.get(COMMAND_TIMEOUT_MS, TimeUnit.MILLISECONDS);
            response.json(result.success ? 200 : 400, GSON.toJson(result));
        } catch (TimeoutException e) {
            response.json(504, "{\"success\":false,\"message\":\"Command timed out waiting for game thread\"}");
        } catch (Exception e) {
            response.json(500, "{\"error\":\"" + escapeJson(e.getMessage()) + "\"}");
        }
    }

    private static String escapeJson(String value) {
        if (value == null) {
            return "";
        }
        return value.replace("\\", "\\\\").replace("\"", "\\\"");
    }
}
