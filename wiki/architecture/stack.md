# Stack

```
┌─────────────────┐     WebSocket      ┌──────────────────┐
│  Dashboard      │◄──────────────────►│  Python bridge   │
│  :3847          │     REST           │  (FastAPI)       │
└─────────────────┘                    └────────┬─────────┘
                                                │
                           OpenRouter / Ollama  │ HTTP
                                                │
                                       ┌────────▼─────────┐
                                       │  LLM Brain       │
                                       │  playbook+memory │
                                       └────────┬─────────┘
                                                │ POST /api/command
                                       ┌────────▼─────────┐
                                       │  LLM Overlord    │
                                       │  Java mod :47823 │
                                       └────────┬─────────┘
                                                │ game thread
                                       ┌────────▼─────────┐
                                       │  Songs of Syx    │
                                       │  0.69.x          │
                                       └──────────────────┘
```

## Tick loop (every ~5s)

1. Bridge GET `/api/state` from mod
2. Load playbook + session memory into prompt
3. LLM returns JSON commands
4. Bridge POST each command to mod (game thread queue)
5. Log results to JSONL memory + dashboard WebSocket
