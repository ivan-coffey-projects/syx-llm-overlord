"""Main entry point for the Syx LLM Overlord bridge service."""
from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, Response
from pydantic import BaseModel

from .config import (
    load_config,
    save_llm_settings,
    save_personality_settings,
    save_game_mode_settings,
    ollama_native_url,
    ollama_request_timeout,
    openrouter_api_key,
    is_openrouter_free_model,
    OPENROUTER_FREE_ALLOWLIST,
    DEFAULT_OLLAMA_URL,
    DEFAULT_OPENROUTER_URL,
    ollama_v1_url_from_config,
    ollama_host_for_display,
    Config,
    PROVIDER_PRESETS,
    OTHER_PROVIDERS,
    PROVIDER_NEEDS_BASE_URL,
    provider_key_env_name,
    resolve_provider_api_key,
    provider_key_status,
    save_api_key,
)
from .game_client import GameClient
from .llm_brain import LLMBrain
from .memory import OverlordMemory
from .knowledge import OverlordKnowledge
from .command_guard import (
    filter_commands,
    apply_timeout_backoff,
    apply_gameplay_adjustments,
    is_timeout_result,
    is_tmparea_result,
    record_build_outcome,
    record_clear_placement_outcome,
    should_clear_placement,
    should_clear_stuck_construction,
    reset_session_guard,
    tick_guard_cooldowns,
    guard_status,
    effective_inject_speed,
)
from .game_session import GameSessionTracker
from .screenshot import (
    capture_game_screenshot,
    latest_screenshot_path,
    save_uploaded_screenshot,
)
from .monitors import (
    apply_monitor,
    list_monitors,
    active_monitor_index,
    display_env,
    launcher_settings_path,
)
from .wiki_sync import sync_memory_to_wiki
from .paths import restart_script_path, repo_root
from .map_pins import MapPinStore
from .personalities import (
    persona_choices,
    game_mode_choices,
    normalize_persona_id,
    normalize_game_mode_id,
    normalize_personality_id,
    get_persona,
    get_game_mode,
)
from .models import GameState, TickRecord, LLMDecision, CommandResult, Command
from . import dashboard as dash_module

logger = logging.getLogger("syx-overlord")


def format_openrouter_price_per_million(price: str | float | None) -> str | None:
    """OpenRouter returns USD per token; format as USD per 1M tokens for display."""
    if price is None:
        return None
    try:
        per_token = float(price)
    except (TypeError, ValueError):
        return None
    if per_token < 0:
        return "varies"
    if per_token == 0:
        return "free"
    per_m = per_token * 1_000_000
    if per_m >= 1:
        return f"${per_m:.2f}/M"
    if per_m >= 0.01:
        return f"${per_m:.3f}/M"
    return f"${per_m:.4f}/M"


# Global state for the decision loop
config: Config | None = None
game_client: GameClient | None = None
llm_brain: LLMBrain | None = None
tick_history: list[TickRecord] = []
ws_clients: set[WebSocket] = set()
running = False
current_state: GameState | None = None
user_orders: list[str] = []
chat_log: list[dict] = []
overlord_memory = OverlordMemory()
overlord_knowledge = OverlordKnowledge()
pending_chat_screenshot: dict | None = None  # path, base64, filename for next chat message
game_session = GameSessionTracker()
map_pin_store = MapPinStore()


class LLMUpdateRequest(BaseModel):
    provider: str = "ollama"
    model: str
    base_url: str | None = None


class ApiKeyUpdateRequest(BaseModel):
    provider: str
    api_key: str


class OllamaWakeRequest(BaseModel):
    model: str | None = None


class InstructRequest(BaseModel):
    message: str
    clear: bool = False
    queue_for_tick: bool = True


class MemoryNoteRequest(BaseModel):
    text: str


class KnowledgeNoteRequest(BaseModel):
    text: str


class PersonalityUpdateRequest(BaseModel):
    personality: str  # persona id (legacy field name)


class GameModeUpdateRequest(BaseModel):
    game_mode: str


class MonitorUpdateRequest(BaseModel):
    index: int
    pin_now: bool = True
    restart: bool = False


class MapPinRequest(BaseModel):
    x: int
    y: int
    label: str = "build here"
    pin_type: str = "custom"
    color: str | None = None
    queue: bool = False


def reload_llm_brain() -> None:
    global llm_brain, config
    if config is None:
        config = load_config()
    if llm_brain:
        llm_brain.close()
    llm_brain = LLMBrain(
        config.llm,
        persona=config.overlord.persona,
        game_mode=config.overlord.game_mode,
        map_llm_enabled=config.map.llm_enabled,
    )
    logger.info(
        f"LLM reloaded: {config.llm.provider}/{config.llm.model} "
        f"persona={config.overlord.persona} game_mode={config.overlord.game_mode} "
        f"map_llm={config.map.llm_enabled}"
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    global config, game_client, llm_brain, running

    config = load_config()
    game_client = GameClient(config.game.mod_url)
    llm_brain = LLMBrain(
        config.llm,
        persona=config.overlord.persona,
        game_mode=config.overlord.game_mode,
        map_llm_enabled=config.map.llm_enabled,
    )

    logging.basicConfig(
        level=getattr(logging, "INFO"),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    logger.info("Syx LLM Overlord bridge starting...")
    logger.info(f"LLM: {config.llm.provider} / {config.llm.model}")
    logger.info(f"Persona: {config.overlord.persona} · Game mode: {config.overlord.game_mode}")
    logger.info(f"Game API: {config.game.mod_url}")
    logger.info(f"Dashboard: http://localhost:{config.dashboard.port}")

    if not overlord_knowledge.path.is_file() or not overlord_knowledge.snapshot()["blacklist_count"]:
        failures = [
            e for e in overlord_memory.entries(limit=500)
            if e.get("kind") == "failure"
        ]
        if failures:
            n = overlord_knowledge.import_failures_from_memory(failures)
            logger.info(f"Knowledge backfill: imported {n} failures from session memory")

    running = True
    loop_task = asyncio.create_task(decision_loop())

    yield

    running = False
    loop_task.cancel()
    if game_client:
        game_client.close()
    if llm_brain:
        llm_brain.close()


app = FastAPI(title="Syx LLM Overlord", lifespan=lifespan)

# Serve dashboard static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


async def broadcast_ws(data: dict):
    """Send data to all connected WebSocket clients."""
    global ws_clients
    dead = set()
    for ws in ws_clients:
        try:
            await ws.send_json(data)
        except Exception:
            dead.add(ws)
    ws_clients -= dead


async def decision_loop():
    """Main loop: poll game state -> LLM decides -> send commands."""
    global current_state
    tick = 0
    recent_history: list[str] = []
    consecutive_timeouts = 0

    while running:
        try:
            tick_guard_cooldowns(current_state)
            # 1. Fetch game state
            try:
                state = await asyncio.get_event_loop().run_in_executor(
                    None, game_client.get_state
                )
                current_state = state
            except Exception as e:
                logger.warning(f"Cannot reach game API: {e}")
                await broadcast_ws({"type": "error", "message": f"Game API unreachable: {e}"})
                await asyncio.sleep(config.game.poll_interval_seconds)
                continue

            if game_session.check_new_game(state):
                tick = 0
                recent_history.clear()
                consecutive_timeouts = 0
                reset_session_guard()
                overlord_knowledge.reset_for_new_game(
                    throne=state.throne,
                    day=state.gameTime.get("day") if state.gameTime else None,
                )
                overlord_memory.clear()
                map_pin_store.clear()
                overlord_memory.append(
                    "New game detected — session memory and coord blacklist cleared.",
                    kind="session",
                )
                logger.info(
                    "New game detected — reset memory, knowledge blacklist, guard state"
                )

            # 2. Get LLM decision
            tick += 1
            mem_context = overlord_memory.for_prompt()
            knowledge_context = overlord_knowledge.for_prompt()
            pins_context = map_pin_store.for_prompt()

            screenshot_b64: str | None = None
            if config.vision.enabled and config.vision.every_n_ticks > 0:
                if tick == 1 or tick % config.vision.every_n_ticks == 0:
                    shot = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: capture_game_screenshot(
                            max_width=config.vision.max_width,
                        ),
                    )
                    if shot.ok and shot.base64_png:
                        screenshot_b64 = shot.base64_png
                        logger.info(
                            f"Tick {tick}: screenshot {shot.path} "
                            f"({shot.width}x{shot.height})"
                        )
                    elif shot.error:
                        logger.warning(f"Tick {tick}: screenshot failed: {shot.error}")

            logger.info(f"Tick {tick}: Getting LLM decision...")
            decision = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda pc=pins_context: llm_brain.decide(
                    state,
                    recent_history,
                    list(user_orders),
                    pc,
                    mem_context,
                    knowledge_context,
                    screenshot_b64,
                    config.vision.model if screenshot_b64 else None,
                ),
            )
            logger.info(f"Tick {tick}: LLM mood={decision.mood}, commands={len(decision.commands)}")
            logger.info(f"Tick {tick}: Reasoning: {decision.reasoning}")

            # 3. Auto-clear TmpArea ghosts before builds when saturated
            if should_clear_placement():
                try:
                    clear_res = await asyncio.get_event_loop().run_in_executor(
                        None,
                        game_client.send_command,
                        Command(action="clear_placement"),
                    )
                    logger.info(
                        f"Tick {tick}: clear_placement "
                        f"{'OK' if clear_res.success else 'FAIL'} - {clear_res.message}"
                    )
                    record_clear_placement_outcome(clear_res.success)
                except Exception as e:
                    logger.warning(f"Tick {tick}: clear_placement error: {e}")

            # 3b. Stalled construction: force builder speed, then instant-finish
            # sites (mod cheat — forest clear backlogs never drain at pop 7).
            # clear_placement alone only frees the placer, not the job queue.
            if should_clear_stuck_construction():
                try:
                    inject = effective_inject_speed(state)
                    speed_res = await asyncio.get_event_loop().run_in_executor(
                        None,
                        game_client.send_command,
                        Command(action="set_speed", params={"value": inject}),
                    )
                    logger.info(
                        f"Tick {tick}: stuck construction — set_speed {inject} "
                        f"{'OK' if speed_res.success else 'FAIL'} - {speed_res.message}"
                    )
                    finish_res = await asyncio.get_event_loop().run_in_executor(
                        None,
                        game_client.send_command,
                        Command(action="finish_construction"),
                    )
                    logger.info(
                        f"Tick {tick}: stuck construction (stalled "
                        f"{guard_status().get('construction_stall_ticks', 0)} ticks) "
                        f"finish_construction "
                        f"{'OK' if finish_res.success else 'FAIL'} - {finish_res.message}"
                    )
                    if not finish_res.success:
                        stuck_res = await asyncio.get_event_loop().run_in_executor(
                            None,
                            game_client.send_command,
                            Command(action="clear_placement"),
                        )
                        logger.info(
                            f"Tick {tick}: finish unavailable — clear_placement "
                            f"{'OK' if stuck_res.success else 'FAIL'} - {stuck_res.message}"
                        )
                        record_clear_placement_outcome(stuck_res.success)
                except Exception as e:
                    logger.warning(f"Tick {tick}: stuck-construction rescue error: {e}")

            # 4. Pre-flight filter + timeout backoff
            raw_commands = decision.commands[: config.game.command_rate_limit]
            raw_commands, gameplay_note = apply_gameplay_adjustments(raw_commands, state)
            if gameplay_note:
                logger.info(f"Tick {tick}: {gameplay_note}")
            allowed, rejected = filter_commands(raw_commands, state, overlord_knowledge)
            commands_to_run, backoff = apply_timeout_backoff(
                allowed, consecutive_timeouts, state
            )
            if backoff and not commands_to_run:
                logger.info(
                    f"Tick {tick}: timeout backoff + construction active — "
                    "skipping commands this tick"
                )
            elif backoff:
                logger.warning(
                    f"Tick {tick}: timeout backoff ({consecutive_timeouts} streak) — "
                    "set_speed only this tick"
                )

            executed_commands: list[Command] = []
            results: list[CommandResult] = []

            for cmd, reason in rejected:
                executed_commands.append(cmd)
                results.append(CommandResult(success=False, message=f"BLOCKED: {reason}"))
                logger.info(f"  Command '{cmd.action}' BLOCKED: {reason}")

            for cmd in commands_to_run:
                try:
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, game_client.send_command, cmd
                    )
                    executed_commands.append(cmd)
                    results.append(result)
                    logger.info(
                        f"  Command '{cmd.action}': "
                        f"{'OK' if result.success else 'FAIL'} - {result.message}"
                    )
                    if cmd.action == "build":
                        record_build_outcome(result.success, result.message, cmd.target)
                        if not result.success and is_tmparea_result(result.message):
                            try:
                                clear_res = await asyncio.get_event_loop().run_in_executor(
                                    None,
                                    game_client.send_command,
                                    Command(action="clear_placement"),
                                )
                                logger.info(
                                    f"  post-fail clear_placement "
                                    f"{'OK' if clear_res.success else 'FAIL'} - {clear_res.message}"
                                )
                                record_clear_placement_outcome(clear_res.success)
                            except Exception as e:
                                logger.warning(f"  post-fail clear_placement error: {e}")
                except Exception as e:
                    executed_commands.append(cmd)
                    results.append(CommandResult(success=False, message=str(e)))
                    logger.error(f"  Command '{cmd.action}' error: {e}")

            if results:
                if any(is_timeout_result(r.message) for r in results):
                    consecutive_timeouts += 1
                elif any(r.success for r in results):
                    consecutive_timeouts = 0

            # 4. Record tick
            record = TickRecord(
                tick_number=tick,
                game_state=state,
                llm_decision=decision,
                command_results=results,
            )
            tick_history.append(record)
            if len(tick_history) > 500:
                tick_history.pop(0)

            # Format history for next prompt
            recent_history.append(
                f"Tick {tick}: {decision.mood} - {decision.reasoning} "
                f"-> {[c.action for c in decision.commands]}"
            )
            recent_history = recent_history[-10:]

            # Persist session memory
            day = state.gameTime.get("day") if state.gameTime else None
            pop = state.population.get("total") if state.population else None
            overlord_memory.log_tick(
                tick,
                day,
                pop,
                state.throne or None,
                decision.reasoning,
                [c.model_dump(exclude_none=True) for c in executed_commands],
                [{"success": r.success, "message": r.message} for r in results],
                knowledge=overlord_knowledge,
            )
            for cmd, res in zip(executed_commands, results):
                if res.message.startswith("BLOCKED:"):
                    overlord_memory.append(
                        f"BLOCKED {cmd.action} {cmd.target} "
                        f"at ({cmd.x},{cmd.y}): {res.message}",
                        kind="blocked",
                        tick=tick,
                        day=day,
                    )
            try:
                sync_memory_to_wiki(
                    overlord_memory.entries(limit=200),
                    source_path=str(overlord_memory.path),
                )
                overlord_knowledge.sync_wiki()
            except OSError as e:
                logger.warning(f"Wiki sync failed: {e}")

            # 5. Broadcast to dashboard
            await broadcast_ws({
                "type": "tick",
                "tick": tick,
                "state": state.model_dump(),
                "guard": guard_status(),
                "decision": {
                    "reasoning": decision.reasoning,
                    "mood": decision.mood,
                    "commands": [c.model_dump(exclude_none=True) for c in decision.commands],
                },
                "results": [{"success": r.success, "message": r.message} for r in results],
                "memory_tail": overlord_memory.entries(limit=8),
            })

        except Exception as e:
            logger.error(f"Decision loop error: {e}", exc_info=True)

        await asyncio.sleep(config.game.poll_interval_seconds)


# --- API Routes ---

@app.get("/", response_class=HTMLResponse)
async def root():
    return dash_module.get_html()


@app.head("/")
async def root_head():
    return Response(status_code=200)


@app.get("/api/health")
async def health():
    game_ok = game_client.health_check() if game_client else False
    return {"status": "ok", "game_connected": game_ok}


@app.get("/api/state")
async def get_state():
    if current_state:
        return current_state.model_dump()
    return {"error": "No state available"}


@app.get("/api/history")
async def get_history():
    return [r.model_dump() for r in tick_history[-50:]]


@app.get("/api/instruct")
async def get_instructions():
    return {"orders": user_orders}


@app.post("/api/instruct")
async def post_instruction(body: InstructRequest):
    global user_orders, chat_log, pending_chat_screenshot
    msg = (body.message or "").strip()
    if body.clear or not msg:
        user_orders = []
        return {"success": True, "message": "Orders cleared", "orders": []}

    recent = [
        f"Tick {r.tick_number}: {r.llm_decision.mood} — {r.llm_decision.reasoning[:180]}"
        for r in tick_history[-5:]
    ]
    mem_context = overlord_memory.for_prompt()
    knowledge_context = overlord_knowledge.for_prompt()

    reply = ""
    screenshot_b64: str | None = None
    if pending_chat_screenshot:
        screenshot_b64 = pending_chat_screenshot.get("base64")
    if llm_brain:
        vision_model = None
        if screenshot_b64 and config:
            vision_model = config.vision.model or config.llm.fallback_model
        reply = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: llm_brain.reply_to_user(
                msg,
                current_state,
                mem_context,
                knowledge_context,
                recent,
                screenshot_b64,
                vision_model,
            ),
        )

    if body.queue_for_tick:
        user_orders.append(msg)
        if len(user_orders) > 10:
            user_orders = user_orders[-10:]
        overlord_memory.log_order(msg)

    overlord_memory.append(f"Player: {msg}", kind="chat_user")
    if reply:
        overlord_memory.append(f"Overlord: {reply}", kind="chat_reply")

    entry = {
        "id": str(uuid.uuid4()),
        "ts": datetime.now(timezone.utc).isoformat(),
        "user": msg,
        "reply": reply,
        "queued": body.queue_for_tick,
        "screenshot": bool(screenshot_b64),
    }
    chat_log.append(entry)
    if len(chat_log) > 100:
        chat_log.pop(0)

    logger.info(f"Player chat: {msg[:80]} -> {reply[:80]}")
    had_screenshot = bool(screenshot_b64)
    if had_screenshot:
        pending_chat_screenshot = None
    await broadcast_ws({
        "type": "chat",
        "id": entry["id"],
        "user": msg,
        "reply": reply,
        "orders": user_orders,
        "queued": body.queue_for_tick,
        "screenshot": had_screenshot,
    })
    return {
        "success": True,
        "message": "Reply from overlord",
        "id": entry["id"],
        "reply": reply,
        "orders": user_orders,
        "queued": body.queue_for_tick,
        "screenshot": had_screenshot,
    }


@app.get("/api/chat")
async def get_chat(limit: int = 50):
    return {"messages": chat_log[-min(limit, 100):]}


@app.get("/api/memory")
async def get_memory(limit: int = 50):
    return {
        "path": str(overlord_memory.path),
        "entries": overlord_memory.entries(limit=min(limit, 200)),
        "prompt_preview": overlord_memory.for_prompt(limit=15),
    }


@app.post("/api/memory")
async def add_memory_note(body: MemoryNoteRequest):
    text = (body.text or "").strip()
    if not text:
        return {"success": False, "message": "Empty note"}
    entry = overlord_memory.append(text, kind="note")
    await broadcast_ws({"type": "memory", "entry": entry})
    return {"success": True, "entry": entry}


@app.delete("/api/memory")
async def clear_memory():
    overlord_memory.clear()
    await broadcast_ws({"type": "memory_cleared"})
    return {"success": True, "message": "Memory log cleared"}


@app.get("/api/knowledge")
async def get_knowledge():
    return overlord_knowledge.snapshot()


@app.post("/api/knowledge")
async def add_knowledge_note(body: KnowledgeNoteRequest):
    text = (body.text or "").strip()
    if not text:
        return {"success": False, "message": "Empty note"}
    overlord_knowledge.record_fact(text)
    overlord_knowledge.sync_wiki()
    snap = overlord_knowledge.snapshot()
    await broadcast_ws({"type": "knowledge", "snapshot": snap})
    return {"success": True, "snapshot": snap}


@app.get("/api/map")
async def get_map():
    """ASCII tile grid from latest game state (full settlement when mod updated)."""
    pins = map_pin_store.snapshot()
    meta = {
        "llm_map_enabled": config.map.llm_enabled if config else False,
    }

    def pack(state: GameState) -> dict:
        out = {
            "centerX": state.mapCenterX,
            "centerY": state.mapCenterY,
            "radius": state.mapRadius,
            "mapFull": state.mapFull,
            "x1": state.mapX1,
            "y1": state.mapY1,
            "x2": state.mapX2,
            "y2": state.mapY2,
            "legend": state.mapLegend,
            "rows": state.mapRows,
            "pins": pins,
            **meta,
        }
        if state.mapFull and state.mapX2 >= state.mapX1:
            out["width"] = state.mapX2 - state.mapX1 + 1
            out["height"] = state.mapY2 - state.mapY1 + 1
        return out

    if current_state and current_state.mapRows:
        return pack(current_state)
    try:
        state = await asyncio.get_event_loop().run_in_executor(
            None, game_client.get_state
        )
        if state.mapRows:
            return pack(state)
    except Exception as e:
        return {"success": False, "message": str(e), "pins": pins, **meta}
    return {
        "success": False,
        "message": "No map grid in state — restart the game to load the updated mod JAR",
        "pins": pins,
        **meta,
    }


@app.get("/api/map/pins")
async def list_map_pins():
    return {"pins": map_pin_store.snapshot()}


@app.post("/api/map/pins")
async def add_map_pin(body: MapPinRequest):
    global user_orders
    pin = map_pin_store.add(
        body.x, body.y, body.label, body.pin_type, body.color
    )
    if body.queue:
        line = pin.order_line()
        user_orders.append(line)
        if len(user_orders) > 10:
            user_orders = user_orders[-10:]
        overlord_memory.log_order(line)
    await broadcast_ws({"type": "map_pins", "pins": map_pin_store.snapshot()})
    return {"success": True, "pin": pin.to_dict(), "pins": map_pin_store.snapshot()}


@app.delete("/api/map/pins/{pin_id}")
async def delete_map_pin(pin_id: str):
    ok = map_pin_store.remove(pin_id)
    await broadcast_ws({"type": "map_pins", "pins": map_pin_store.snapshot()})
    return {"success": ok, "pins": map_pin_store.snapshot()}


@app.delete("/api/map/pins")
async def clear_map_pins():
    map_pin_store.clear()
    await broadcast_ws({"type": "map_pins", "pins": []})
    return {"success": True, "pins": []}


@app.post("/api/map/pins/queue")
async def queue_map_pins():
    """Push all pins into the overlord order queue for the next tick."""
    global user_orders
    lines = map_pin_store.queue_lines()
    for line in lines:
        user_orders.append(line)
    if len(user_orders) > 10:
        user_orders = user_orders[-10:]
    for line in lines:
        overlord_memory.log_order(line)
    await broadcast_ws({"type": "map_pins", "pins": map_pin_store.snapshot(), "orders": user_orders})
    return {"success": True, "queued": lines, "orders": user_orders}


@app.post("/api/screenshot")
async def take_screenshot():
    """Capture the game window now (xdotool + ImageMagick import)."""
    global pending_chat_screenshot
    shot = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: capture_game_screenshot(
            max_width=config.vision.max_width if config else 1024,
        ),
    )
    if shot.ok and shot.base64_png and shot.path:
        pending_chat_screenshot = {
            "path": str(shot.path),
            "base64": shot.base64_png,
            "filename": shot.path.name,
            "width": shot.width,
            "height": shot.height,
        }
    return {
        "success": shot.ok,
        "path": str(shot.path) if shot.path else None,
        "width": shot.width,
        "height": shot.height,
        "window_id": shot.window_id,
        "error": shot.error,
        "attached": bool(shot.ok),
        "preview_url": "/api/screenshot/pending/image" if shot.ok else None,
    }


@app.get("/api/screenshot/latest")
async def get_latest_screenshot():
    """Return the most recent settlement PNG."""
    path = latest_screenshot_path()
    if path and path.is_file():
        return FileResponse(path, media_type="image/png", filename=path.name)
    return {"success": False, "message": "No screenshot captured yet"}


@app.get("/api/screenshot/pending")
async def get_pending_screenshot():
    """Attached screenshot for the next chat message."""
    if pending_chat_screenshot and pending_chat_screenshot.get("path"):
        p = Path(pending_chat_screenshot["path"])
        if p.is_file():
            return {
                "attached": True,
                "path": str(p),
                "filename": pending_chat_screenshot.get("filename", p.name),
                "width": pending_chat_screenshot.get("width"),
                "height": pending_chat_screenshot.get("height"),
                "preview_url": "/api/screenshot/pending/image",
            }
    return {"attached": False}


@app.get("/api/screenshot/pending/image")
async def get_pending_screenshot_image():
    if pending_chat_screenshot and pending_chat_screenshot.get("path"):
        p = Path(pending_chat_screenshot["path"])
        if p.is_file():
            return FileResponse(p, media_type="image/png", filename=p.name)
    return {"success": False, "message": "No screenshot attached"}


@app.delete("/api/screenshot/pending")
async def clear_pending_screenshot():
    global pending_chat_screenshot
    pending_chat_screenshot = None
    return {"success": True, "attached": False}


@app.post("/api/screenshot/upload")
async def upload_screenshot(file: UploadFile = File(...)):
    """Upload a PNG/JPEG for the overlord to see in chat."""
    global pending_chat_screenshot
    data = await file.read()
    max_w = config.vision.max_width if config else 1024
    shot = save_uploaded_screenshot(
        data,
        file.filename or "upload.png",
        max_width=max_w,
    )
    if not shot.ok:
        return {"success": False, "error": shot.error}
    pending_chat_screenshot = {
        "path": str(shot.path),
        "base64": shot.base64_png,
        "filename": file.filename or shot.path.name,
        "width": shot.width,
        "height": shot.height,
    }
    return {
        "success": True,
        "path": str(shot.path),
        "filename": pending_chat_screenshot["filename"],
        "width": shot.width,
        "height": shot.height,
        "preview_url": "/api/screenshot/pending/image",
    }


@app.post("/api/playbook/reload")
async def reload_playbook():
    """Pick up Obsidian wiki playbook edits (re-read on next tick automatically)."""
    from .playbook import load_playbook, VAULT_PLAYBOOK
    text = load_playbook()
    return {
        "success": True,
        "path": str(VAULT_PLAYBOOK),
        "loaded": VAULT_PLAYBOOK.is_file(),
        "chars": len(text),
        "message": "Playbook re-read; next LLM tick uses latest wiki content",
    }


@app.get("/api/config")
async def get_config():
    if config:
        or_key = openrouter_api_key()
        ollama_v1 = ollama_v1_url_from_config(config)
        other_status = provider_key_status()
        return {
            "llm_provider": config.llm.provider,
            "llm_model": config.llm.model,
            "llm_base_url": config.llm.base_url or (
                DEFAULT_OPENROUTER_URL if config.llm.provider == "openrouter" else (ollama_v1 or DEFAULT_OLLAMA_URL)
            ),
            "personality": config.overlord.persona,
            "persona": config.overlord.persona,
            "personality_name": get_persona(config.overlord.persona).name,
            "personality_label": get_persona(config.overlord.persona).chat_label,
            "game_mode": config.overlord.game_mode,
            "game_mode_name": get_game_mode(config.overlord.game_mode).name,
            "game_mode_description": get_game_mode(config.overlord.game_mode).description,
            "personalities": persona_choices(),
            "game_modes": game_mode_choices(),
            "ollama_active": config.llm.provider == "ollama",
            "ollama_url": ollama_host_for_display(config),
            "ollama_v1_url": ollama_v1 or DEFAULT_OLLAMA_URL.rstrip("/"),
            "openrouter_url": DEFAULT_OPENROUTER_URL,
            "openrouter_configured": bool(or_key),
            "other_providers": [
                {
                    "id": p,
                    "label": "Generic (base URL + key)" if p == "api" else p.capitalize(),
                    "configured": other_status.get(p, False),
                    "env_var": provider_key_env_name(p),
                    "base_url_default": PROVIDER_PRESETS.get(p, (None, None))[0],
                    "model_default": PROVIDER_PRESETS.get(p, (None, None))[1],
                    "needs_base_url": p in PROVIDER_NEEDS_BASE_URL,
                }
                for p in OTHER_PROVIDERS
            ],
            "poll_interval": config.game.poll_interval_seconds,
            "game_url": config.game.mod_url,
            "vision_enabled": config.vision.enabled,
            "vision_every_n_ticks": config.vision.every_n_ticks,
            "vision_model": config.vision.model,
        }
    return {}


@app.get("/api/monitors")
async def get_monitors():
    """List game monitor map (GLFW index ↔ XRandR) and active selection."""
    monitors = list_monitors()
    env = display_env()
    return {
        "success": True,
        "active_index": active_monitor_index(),
        "display": env.get("DISPLAY", ":0"),
        "launcher_settings": str(launcher_settings_path()),
        "monitors": [
            {
                "index": m.index,
                "label": m.label,
                "xrandr": m.xrandr,
                "connected": m.connected,
                "geometry": m.geometry,
                "width": m.width,
                "height": m.height,
                "active": m.active,
            }
            for m in monitors
        ],
    }


@app.post("/api/monitors")
async def set_monitor(body: MonitorUpdateRequest):
    """Set game MONITOR index in LauncherSettings + syx.launch.conf."""
    result = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: apply_monitor(body.index, pin_now=body.pin_now),
    )
    if not result.get("success"):
        return result

    if body.restart:
        restart_resp = await restart_game()
        result["restart"] = restart_resp

    await broadcast_ws({
        "type": "monitor",
        "active_index": body.index,
        "xrandr": result.get("xrandr"),
    })
    return result


@app.get("/api/ollama/models")
async def list_ollama_models():
    """Fetch model list from local Ollama — only when Ollama is the active provider."""
    import httpx

    if not config or config.llm.provider != "ollama":
        return {
            "success": False,
            "skipped": True,
            "error": "Ollama is not active — Apply Ollama as provider first (keeps local VRAM free while using OpenRouter).",
            "models": [],
        }
    ollama_v1 = ollama_v1_url_from_config(config)
    if not ollama_v1:
        return {"success": False, "error": "Ollama URL not configured", "models": []}
    url = f"{ollama_native_url(ollama_v1)}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            payload = resp.json()
        models = []
        for entry in payload.get("models", []):
            name = entry.get("name") or entry.get("model")
            if not name:
                continue
            details = entry.get("details") or {}
            caps = entry.get("capabilities") or []
            if caps and "completion" not in caps:
                continue  # embedding-only models can't serve chat decisions
            models.append({
                "name": name,
                "size_gb": round((entry.get("size") or 0) / 1e9, 1),
                "family": details.get("family", ""),
                "params": details.get("parameter_size", ""),
                "quant": details.get("quantization_level", ""),
                "capabilities": caps,
            })
        models.sort(key=lambda m: m["name"].lower())
        return {"success": True, "url": url, "models": models}
    except Exception as e:
        logger.error(f"Ollama model list failed: {e}")
        return {"success": False, "url": url, "error": str(e), "models": []}


@app.get("/api/openrouter/models")
async def list_openrouter_models(free_only: bool = True):
    """Fetch model list from OpenRouter (free tier only by default)."""
    import httpx

    key = openrouter_api_key()
    if not key:
        return {
            "success": False,
            "error": "OPENROUTER_API_KEY not set in environment",
            "models": [],
            "free_only": free_only,
        }
    url = f"{DEFAULT_OPENROUTER_URL}/models"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {key}"})
            resp.raise_for_status()
            payload = resp.json()
        models = []
        for entry in payload.get("data", []):
            mid = entry.get("id")
            if not mid:
                continue
            pricing = entry.get("pricing") or {}
            prompt_raw = pricing.get("prompt")
            completion_raw = pricing.get("completion")
            if free_only and not is_openrouter_free_model(mid, prompt_raw, completion_raw):
                continue
            models.append({
                "name": mid,
                "context": entry.get("context_length"),
                "prompt_price": prompt_raw,
                "completion_price": completion_raw,
                "prompt_price_label": format_openrouter_price_per_million(prompt_raw),
                "completion_price_label": format_openrouter_price_per_million(completion_raw),
            })
        models.sort(key=lambda m: m["name"].lower())

        # Pinned free models — usable even when absent from OpenRouter catalog (preview/retired).
        pinned_ids = [m for m in OPENROUTER_FREE_ALLOWLIST if m not in {x["name"] for x in models}]
        for pid in sorted(pinned_ids):
            models.insert(0, {
                "name": pid,
                "context": None,
                "prompt_price": "0",
                "completion_price": "0",
                "prompt_price_label": "free",
                "completion_price_label": "free",
                "pinned": True,
            })

        return {"success": True, "url": url, "models": models, "free_only": free_only}
    except Exception as e:
        logger.error(f"OpenRouter model list failed: {e}")
        return {"success": False, "url": url, "error": str(e), "models": [], "free_only": free_only}


@app.post("/api/ollama/wake")
async def wake_ollama(body: OllamaWakeRequest | None = None):
    """Load/warm the Ollama model — only when Ollama is the active provider."""
    import httpx

    if not config or config.llm.provider != "ollama":
        return {
            "success": False,
            "skipped": True,
            "error": "Ollama is not active — Apply Ollama as provider before Wake (loads VRAM on local Ollama).",
        }

    model = (body.model if body and body.model else None) or config.llm.model
    ollama_v1 = ollama_v1_url_from_config(config)
    if not ollama_v1:
        return {"success": False, "error": "Ollama URL not configured"}
    root = ollama_native_url(ollama_v1)
    timeout = ollama_request_timeout()

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # Check what's loaded
            ps_resp = await client.get(f"{root}/api/ps")
            loaded = []
            if ps_resp.status_code == 200:
                loaded = [m.get("name") for m in ps_resp.json().get("models", [])]

            # Warm via chat API (same path the brain uses)
            chat_url = f"{ollama_v1.rstrip('/')}/chat/completions"
            t0 = datetime.now()
            resp = await client.post(
                chat_url,
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 8,
                    "stream": False,
                },
            )
            resp.raise_for_status()
            elapsed = (datetime.now() - t0).total_seconds()

        return {
            "success": True,
            "model": model,
            "elapsed_s": round(elapsed, 1),
            "was_loaded": model in loaded or any(model in (x or "") for x in loaded),
            "message": f"Model {model} warm ({elapsed:.1f}s)",
        }
    except Exception as e:
        logger.error(f"Ollama wake failed: {e}")
        return {"success": False, "model": model, "error": str(e)}


@app.post("/api/config/llm")
async def update_llm_config(body: LLMUpdateRequest):
    global config
    try:
        if body.provider == "openrouter":
            if not openrouter_api_key():
                return {"success": False, "message": "OPENROUTER_API_KEY not set in environment"}
            if not is_openrouter_free_model(body.model):
                return {
                    "success": False,
                    "message": (
                        f"Only OpenRouter :free models allowed — "
                        f"{body.model} is not on the free tier"
                    ),
                }
            base_url = body.base_url or DEFAULT_OPENROUTER_URL
        elif body.provider == "ollama":
            base_url = body.base_url or DEFAULT_OLLAMA_URL
        elif body.provider in OTHER_PROVIDERS:
            if not resolve_provider_api_key(body.provider):
                env_name = provider_key_env_name(body.provider)
                return {
                    "success": False,
                    "message": f"{env_name} not set — add a key in the Other Providers panel first",
                }
            preset_url = PROVIDER_PRESETS.get(body.provider, (None, None))[0]
            base_url = body.base_url or preset_url
            if body.provider in PROVIDER_NEEDS_BASE_URL and not base_url:
                return {"success": False, "message": f"Provider '{body.provider}' requires a base_url"}
        else:
            return {"success": False, "message": f"Unsupported provider: {body.provider}"}

        save_llm_settings(provider=body.provider, model=body.model, base_url=base_url)
        config = load_config()
        reload_llm_brain()
        return {
            "success": True,
            "message": f"Now using {config.llm.model}",
            "llm_provider": config.llm.provider,
            "llm_model": config.llm.model,
            "llm_base_url": config.llm.base_url,
        }
    except Exception as e:
        logger.error(f"LLM config update failed: {e}")
        return {"success": False, "message": str(e)}


@app.post("/api/config/apikey")
async def update_api_key(body: ApiKeyUpdateRequest):
    """Save a provider's API key to the user env file. Never echo it or write it to config.yaml."""
    if body.provider not in OTHER_PROVIDERS:
        return {"success": False, "message": f"Unknown provider: {body.provider}"}
    key = body.api_key.strip()
    if not key:
        return {"success": False, "message": "API key is empty"}
    try:
        env_name = save_api_key(body.provider, key)
        return {"success": True, "provider": body.provider, "env_var": env_name, "configured": True}
    except Exception as e:
        logger.error(f"API key save failed: {e}")
        return {"success": False, "message": str(e)}


@app.post("/api/config/personality")
async def update_personality(body: PersonalityUpdateRequest):
    global config
    try:
        pid = normalize_persona_id(body.personality)
        save_personality_settings(personality=pid)
        config = load_config()
        if llm_brain:
            llm_brain.set_persona(pid)
        p = get_persona(pid)
        await broadcast_ws({
            "type": "persona",
            "persona": pid,
            "personality": pid,
            "personality_name": p.name,
            "personality_label": p.chat_label,
        })
        return {
            "success": True,
            "message": f"Persona set to {p.name}",
            "persona": pid,
            "personality": pid,
            "personality_name": p.name,
            "personality_label": p.chat_label,
        }
    except Exception as e:
        logger.error(f"Persona update failed: {e}")
        return {"success": False, "message": str(e)}


@app.post("/api/config/game-mode")
async def update_game_mode(body: GameModeUpdateRequest):
    global config
    try:
        mid = normalize_game_mode_id(body.game_mode)
        save_game_mode_settings(game_mode=mid)
        config = load_config()
        if llm_brain:
            llm_brain.set_game_mode(mid)
        g = get_game_mode(mid)
        await broadcast_ws({
            "type": "game_mode",
            "game_mode": mid,
            "game_mode_name": g.name,
            "game_mode_description": g.description,
        })
        return {
            "success": True,
            "message": f"Game mode set to {g.name}",
            "game_mode": mid,
            "game_mode_name": g.name,
            "game_mode_description": g.description,
        }
    except Exception as e:
        logger.error(f"Game mode update failed: {e}")
        return {"success": False, "message": str(e)}


@app.post("/api/restart")
async def restart_game():
    """Restart Songs of Syx without spawning a second syx launcher."""
    import os
    import subprocess

    if os.environ.get("SYX_DISABLE_GAME_LAUNCH", "").strip().lower() in ("1", "true", "yes"):
        return {
            "success": False,
            "message": (
                "Game launch disabled (SYX_DISABLE_GAME_LAUNCH). "
                "Use staging VM for automated game tests — do not restart on Ivan's desktop."
            ),
        }

    script = str(restart_script_path())
    env = os.environ.copy()
    repo = str(repo_root())
    env.setdefault("SYX_OVERLORD_ROOT", repo)

    # Load API keys / paths from repo .env
    dotenv = repo_root() / ".env"
    if dotenv.is_file():
        for line in dotenv.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip('"').strip("'")
            if key and val and key not in env:
                env[key] = val

    user_env = Path(
        os.environ.get(
            "SYX_USER_ENV",
            Path.home() / ".config" / "syx-llm-overlord" / ".env",
        )
    )
    if user_env.is_file():
        for line in user_env.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip('"').strip("'")
            if key and val:
                env[key] = val

    try:
        if not Path(script).exists():
            return {"success": False, "message": f"Script not found: {script}"}

        logger.info(f"Restart via {script} DISPLAY={env.get('DISPLAY', 'unset')}")

        result = subprocess.run(
            ["bash", script],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
            cwd=str(Path(script).parent.parent),
        )
        if result.returncode != 0:
            tail = (result.stderr or result.stdout or "").strip()[-500:]
            return {"success": False, "message": f"Restart script failed: {tail}"}

        return {
            "success": True,
            "message": "Game relaunching (bridge unchanged)",
            "script": script,
        }
    except Exception as e:
        logger.error(f"Restart failed: {e}")
        return {"success": False, "message": str(e)}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    ws_clients.add(ws)
    logger.info(f"Dashboard client connected ({len(ws_clients)} total)")
    try:
        # Send current state immediately
        if current_state:
            await ws.send_json({"type": "state", "state": current_state.model_dump()})
        # Keep connection alive
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ws_clients.discard(ws)
        logger.info(f"Dashboard client disconnected ({len(ws_clients)} total)")


def main():
    import uvicorn
    cfg = load_config()
    uvicorn.run(
        "bridge.main:app",
        host="0.0.0.0",
        port=cfg.dashboard.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
