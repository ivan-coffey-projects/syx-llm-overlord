# Syx LLM Overlord

Watch an LLM rule your Songs of Syx settlement — reads game state, builds rooms, remembers failures, and **talks back** when you ask questions.

```
Game (Java mod :47823) → Python bridge (:3847) → Ollama local OR cloud API
                              ↓
                     Dashboard + wiki playbook
```

**Requires:** a copy of [Songs of Syx](https://store.steampowered.com/app/1162750/Songs_of_Syx/) (any recent version), Java 21, Python 3.11+.

---

## Quick start

```bash
git clone https://github.com/ivan-coffey-projects/syx-llm-overlord.git
cd syx-llm-overlord

cp .env.example .env          # add API key if using cloud models
./install.sh                  # venv, build mod, write config
./run.sh                      # start bridge → http://localhost:3847
```

Launch **Songs of Syx** from Steam, enable the **LLM Overlord** mod, start a game, open the dashboard, and use **Talk to the Overlord**.

---

## Choose your LLM

### Option A — Local (Ollama)

No API key. Runs on your machine or a LAN server.

1. Install [Ollama](https://ollama.com/) and pull a model, e.g. `ollama pull qwen2.5:14b`
2. Edit `bridge/config.yaml`:

```yaml
llm:
  provider: ollama
  model: qwen2.5:14b
  base_url: http://localhost:11434/v1   # or http://YOUR_SERVER:11434/v1
```

3. Dashboard → **Ollama** tab → **Wake / Load Model** if cold → **Apply**

### Option B — Cloud API (OpenRouter free tier)

Uses OpenRouter’s **`:free` models** only (no paid picks in the dashboard). You still need an OpenRouter API key; usage stays on the free tier.

1. Copy `.env.example` → `.env`
2. Set `OPENROUTER_API_KEY=sk-or-...`
3. Edit `bridge/config.yaml`:

```yaml
llm:
  provider: openrouter
  model: openrouter/owl-alpha
  fallback_model: meta-llama/llama-3.3-70b-instruct:free
```

4. Dashboard → **Settings** → **OpenRouter** → pick a free model → **Apply**

Free models can hit rate limits; the bridge retries with `fallback_model` if set. For zero cloud usage, use **Option A (Ollama)**.

Other paid providers: see comments in `bridge/config.example.yaml` (OpenAI, Together, Groq, DeepSeek, generic `api`).

---

## In-game setup

The mod does **not** auto-start the game. After `./run.sh`:

1. Open Songs of Syx launcher
2. Click **Launch**
3. Select mod **LLM Overlord** in the list
4. **Play** → **random game** (or load a save) → **go!**
5. When the mod API is live, the dashboard shows green status and ticks begin

Mod HTTP API: `http://localhost:47823`
Dashboard: `http://localhost:3847`

---

## Talk to the overlord

Use the dashboard **Talk to the Overlord** panel (not in-game chat):

- **Questions** → immediate plain-text reply (“Why did the well fail?”)
- **Orders** → reply + queued for the next decision tick (“Build homes near throne”)

API: `POST /api/instruct` with `{"message": "..."}` → returns `{"reply": "..."}`.

---

## What works today

| Action | Status |
|--------|--------|
| `build` | ✅ Real room placement via game API |
| `set_speed` | ✅ Pause / slow / normal / fast |
| `demolish`, `set_policy`, `recruit`, `set_tax`, `set_ration` | ⚠️ Stubbed — documented, not implemented |

See `wiki/rules/commands.md` for details. We ship with stubs documented and will enable more over time.

---

## Wiki & memory

| Path | Purpose |
|------|---------|
| `wiki/rules/playbook.md` | Strategy rules — injected every LLM tick |
| `logs/overlord-memory.jsonl` | Session memory (failures, orders, chat) |
| `wiki/memory/live-log.md` | Auto-updated mirror for Obsidian |

Edit the playbook while the bridge runs — next tick picks up changes.

Optional: open `wiki/` as an Obsidian vault folder.

---

## Game version

`install.sh` auto-detects your game version folder (`V69`, `V70`, …) from installed mods or game files.

Override manually:

```bash
export SYX_GAME_VERSION=V70
export SONGSOFSYX_JAR=/path/to/SongsOfSyx.jar
./install.sh
```

---

## Commands

```bash
./install.sh          # first-time setup
./run.sh              # mod check + bridge + instructions
./run.sh build        # rebuild mod only
./run.sh bridge       # bridge only

# API examples
curl -X POST http://localhost:3847/api/instruct \
  -H 'Content-Type: application/json' \
  -d '{"message":"What should we build first?"}'

curl -X POST http://localhost:3847/api/restart   # relaunch game (see scripts/restart-game-only.sh)
```

---

## Project layout

```
syx-llm-mod/     Java mod (HTTP API inside the game)
bridge/          Python FastAPI + dashboard + LLM brain
wiki/            Playbook and docs (Obsidian-friendly)
scripts/         find-game-jar, detect version, restart game
install.sh       First-time setup
run.sh           Start bridge
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Dashboard red / no ticks | Load into a settlement; mod API only runs in-game |
| `Game API unreachable` | Enable LLM Overlord mod; check `:47823` |
| Builds at (0,0) | Throne coords missing — load save, check state panel |
| TmpArea / PlacerItem crash | Restart game via dashboard; avoid spam-building same tile |
| OpenRouter errors | Set `OPENROUTER_API_KEY` in `.env`, restart bridge; use `:free` models only |
| OpenRouter 429 rate limit | Switch free model in Settings or set `fallback_model` to another `:free` slug |
| Ollama timeout | Use **Wake / Load Model** in dashboard; check `base_url` |

---

## License

MIT — Songs of Syx is a separate commercial product by Gamatron AB. You must own the game. The mod compiles against your local `SongsOfSyx.jar` at build time only.

---

## Project status

Experimental portfolio release. Offline bridge logic is covered by automated tests. Live end-to-end control requires a local Songs of Syx installation and an active game session.
