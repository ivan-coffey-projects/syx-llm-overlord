> **Note:** This is an internal development document. For contributing guidelines, see CONTRIBUTING.md.
>

# Syx LLM Overlord -- Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a system that lets LLMs play Songs of Syx by reading game state through a Java mod and issuing commands via an external Python bridge with a real-time web dashboard for observation.

**Architecture:** Three-layer system: (1) Java mod inside the game exposes HTTP API for state reading and command execution, (2) Python FastAPI bridge polls state, sends to LLM, parses decisions, queues commands, (3) Single-page web dashboard shows live game state, LLM reasoning, and command history via WebSocket.

**Tech Stack:** Java 21 (mod), Python 3.11+ (bridge), FastAPI + Uvicorn (API server), OpenAI/Anthropic/Ollama (LLM), WebSocket (real-time dashboard), Pydantic (data models), httpx (HTTP client)

---

## Project Structure

```
syx-llm-overlord/
├── README.md
├── .gitignore
├── syx-llm-mod/                        # Java mod (runs inside Songs of Syx)
│   ├── pom.xml
│   └── src/main/java/syx/llm/overlord/
│       ├── LlmOverlordScript.java      # SCRIPT implementation, HTTP server lifecycle
│       ├── StateReader.java             # Game state extraction via reflection
│       ├── CommandExecutor.java         # Command validation and execution
│       ├── GameState.java               # State data model
│       ├── Command.java                 # Command data model
│       └── CommandResult.java           # Execution result model
├── bridge/                             # Python bridge service
│   ├── requirements.txt
│   ├── config.example.yaml
│   └── bridge/
│       ├── __init__.py
│       ├── __main__.py
│       ├── main.py                     # FastAPI app, decision loop, WebSocket
│       ├── config.py                   # YAML config loader
│       ├── models.py                   # Pydantic models
│       ├── game_client.py              # HTTP client for mod API
│       ├── llm_brain.py                # LLM prompt formatting and parsing
│       └── dashboard.py                # HTML dashboard generation
└── docs/
    └── plan.md                         # This file
```

---

## Task 1: Java Mod -- HTTP API Server

**Files:**
- Create: `syx-llm-mod/src/main/java/syx/llm/overlord/LlmOverlordScript.java`
- Create: `syx-llm-mod/src/main/java/syx/llm/overlord/GameState.java`
- Create: `syx-llm-mod/src/main/java/syx/llm/overlord/Command.java`
- Create: `syx-llm-mod/src/main/java/syx/llm/overlord/CommandResult.java`

**Goal:** The mod hooks into the game via the `SCRIPT` interface and starts an embedded HTTP server on port 47823 that serves game state as JSON and accepts command POSTs.

- [x] **Step 1: Create `GameState.java` data model**

```java
package syx.llm.overlord;
import java.util.*;
public class GameState {
    public long timestamp;
    public Map<String, Object> population;
    public Map<String, Object> resources;
    public Map<String, Object> happiness;
    public Map<String, Object> roomCounts;
    public Map<String, Object> military;
    public Map<String, Object> diplomacy;
    public Map<String, Object> gameTime;
    public List<String> errors = new ArrayList<>();
}
```

- [x] **Step 2: Create `Command.java` and `CommandResult.java`**

```java
// Command.java
package syx.llm.overlord;
import java.util.Map;
public class Command {
    public String action;
    public String target;
    public Integer x;
    public Integer y;
    public Map<String, Object> params;
}

// CommandResult.java
package syx.llm.overlord;
public class CommandResult {
    public boolean success;
    public String message;
    public CommandResult(boolean success, String message) {
        this.success = success;
        this.message = message;
    }
}
```

- [x] **Step 3: Create `LlmOverlordScript.java` with HTTP server**

Uses `com.sun.net.httpserver.HttpServer` (built into JDK) on port 47823.
Endpoints: `GET /api/state`, `POST /api/command`, `GET /api/health`, `GET /api/info`.
Implements `script.SCRIPT` interface with `initBeforeGameInited()` and `initBeforeGameCreated()`.

- [ ] **Step 4: Create `pom.xml` with Maven build config**

Builds against game JAR, packages mod, copies to game mods folder.

- [ ] **Step 5: Test compilation** (requires game JAR)

Run: `cd syx-llm-mod && mvn validate && mvn package`

---

## Task 2: Java Mod -- State Reader

**Files:**
- Create: `syx-llm-mod/src/main/java/syx/llm/overlord/StateReader.java`

**Goal:** Reads game state from Songs of Syx internal singletons (`game.GAME`, `settlement.main.SETT`, `settlement.stats.STATS`, `game.faction.FACTIONS`) via reflection, since most fields are package-private.

- [x] **Step 1: Implement reflection helpers**

Methods: `getStaticSingleton()`, `getStaticField()`, `invokeMethod()` that handle
the UPPERCASE singleton pattern used by Songs of Syx.

- [x] **Step 2: Implement state readers for each subsystem**

`readPopulation()`, `readResources()`, `readHappiness()`, `readRooms()`,
`readMilitary()`, `readDiplomacy()`, `readTime()` -- each with error isolation.

---

## Task 3: Java Mod -- Command Executor

**Files:**
- Create: `syx-llm-mod/src/main/java/syx/llm/overlord/CommandExecutor.java`

**Goal:** Validates and executes commands from the LLM. Supports: build, demolish, set_policy, recruit, set_tax, set_ration, set_speed, pause. Each action validates required fields before execution.

- [x] **Step 1: Implement command validation and dispatch**

Switch-based dispatch with input validation. Returns `CommandResult` with success/error.

---

## Task 4: Python Bridge -- Models and Config

**Files:**
- Create: `bridge/bridge/__init__.py`
- Create: `bridge/bridge/models.py`
- Create: `bridge/bridge/config.py`
- Create: `bridge/config.example.yaml`
- Create: `bridge/requirements.txt`

**Goal:** Pydantic models for GameState, Command, LLMDecision, TickRecord. YAML config loader with env var substitution.

- [x] **Step 1: Create Pydantic models**
- [x] **Step 2: Create config loader**
- [x] **Step 3: Create requirements.txt and example config**

---

## Task 5: Python Bridge -- Game Client

**Files:**
- Create: `bridge/bridge/game_client.py`

**Goal:** HTTP client that talks to the Java mod's API. Methods: `health_check()`, `get_state()`, `send_command()`, `get_info()`.

- [x] **Step 1: Implement GameClient with httpx**

---

## Task 6: Python Bridge -- LLM Brain

**Files:**
- Create: `bridge/bridge/llm_brain.py`

**Goal:** Formats game state into structured prompts, sends to LLM (OpenAI/Anthropic/Ollama), parses JSON decision response. Includes system prompt with game context and available actions.

- [x] **Step 1: Write system prompt with game rules and JSON output format**
- [x] **Step 2: Implement OpenAI/Ollama provider**
- [x] **Step 3: Implement Anthropic provider**
- [x] **Step 4: Implement JSON response parser with markdown fence stripping**

---

## Task 7: Python Bridge -- Main Loop and API

**Files:**
- Create: `bridge/bridge/main.py`
- Create: `bridge/bridge/__main__.py`

**Goal:** FastAPI app with async decision loop. Polls game state, gets LLM decision, executes commands, broadcasts to WebSocket clients. REST endpoints for health, state, history, config.

- [x] **Step 1: Create FastAPI app with lifespan**
- [x] **Step 2: Implement async decision loop**
- [x] **Step 3: Implement WebSocket broadcast**
- [x] **Step 4: Implement REST endpoints**
- [x] **Step 5: Create __main__.py entry point**

---

## Task 8: Web Dashboard

**Files:**
- Create: `bridge/bridge/dashboard.py`

**Goal:** Dark fantasy-themed single-page dashboard showing live game state, LLM reasoning, and command history. Connects via WebSocket for real-time updates.

- [x] **Step 1: Create HTML with CSS styling**
- [x] **Step 2: Implement WebSocket client and state rendering**
- [x] **Step 3: Implement thought display and command chronicle**

---

## Task 9: Integration and README

**Files:**
- Create: `README.md`
- Create: `.gitignore`

- [x] **Step 1: Write comprehensive README**
- [x] **Step 2: Create .gitignore**

---

## Notes for Implementation

### Game Installation Required
The Java mod needs Songs of Syx installed to compile (game JAR as dependency).
Install via Steam or itch.io, then set `game.jar.path` in pom.xml.

### Modding Constraints
- Game code uses package-private access extensively; reflection is necessary
- The `SCRIPT` interface only provides `initBeforeGameInited()` and `initBeforeGameCreated()` hooks
- No built-in game loop callback; the HTTP server runs on its own thread
- Thread safety: state snapshots must be synchronized with the game thread

### LLM Provider Flexibility
The bridge supports three providers:
- **OpenAI**: GPT-4o, GPT-4-turbo, etc.
- **Ollama**: Local models (llama3, mistral, etc.) via OpenAI-compatible API
- **Anthropic**: Claude models

### Future Enhancements
- Screenshot capture for visual state (requires headless game rendering)
- Multi-LLM competition (different LLMs control different factions)
- Replay system to review LLM decision-making
- Discord/Twitch integration for streaming LLM gameplay
