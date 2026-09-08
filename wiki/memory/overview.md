# Memory system overview

The overlord has **three layers of memory**:

## 1. Playbook (static rules — keep short)

- Wiki: [../rules/playbook](../rules/playbook.md)
- Read **every tick** from `wiki/rules/playbook.md`
- Core facts and day-0 priorities only — not a growing rule dump

## 2. Session memory (this game)

- File: `logs/overlord-memory.jsonl` (or `SYX_MEMORY_PATH`)
- Append-only JSONL — survives bridge restarts
- Last ~30 entries injected as **SESSION MEMORY** each tick
- Live mirror: [live-log](live-log.md)

## 3. Persistent knowledge (all games)

- File: `logs/overlord-knowledge.json` (or `SYX_KNOWLEDGE_PATH`)
- **Survives new games and bridge restarts**
- Auto-learns from failures: blacklists coords after 2 failures at the same spot; promotes patterns (TmpArea, woodcutter/stockpile deadlock) after repeated hits
- Injected as **PERSISTENT KNOWLEDGE** each tick
- Live mirror: [knowledge](knowledge.md)
- Manual facts: `POST /api/knowledge` with `{"text": "..."}`

### What gets logged automatically

| Kind | When |
|------|------|
| `tick` | Every decision cycle |
| `failure` | Each failed command → also feeds persistent knowledge |
| `order` | Player direct order |
| `note` | Manual note via API |

### Why three layers

- **Playbook** = stable game facts you edit by hand
- **Session memory** = this run's diary (orders, recent failures)
- **Persistent knowledge** = learned blacklists and patterns so the LLM stops hammering saturated tiles across sessions

### Chat with the overlord

Dashboard **Talk to the Overlord** uses session memory + persistent knowledge + playbook in chat replies.
