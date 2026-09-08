# Command API

What the mod actually executes vs what the LLM is told exists.

## Working commands

| Action | Params | Notes |
|--------|--------|-------|
| `build` | `target`, `x`, `y`, optional `params.width/height/group` | Real room placement via game API |
| `set_speed` | `params.value` 0–4 | 0=pause, 2=normal, 4=fastest |
| `pause` | — | Sets speed to 0 |
| `info` | — | Returns ruler/pop/faction snapshot |

## Stubs (do not rely on)

| Action | Status |
|--------|--------|
| `set_policy` | Logged only |
| `recruit` | Logged only |
| `set_tax` | Logged only |
| `set_ration` | Logged only |
| `demolish` | Not implemented |

## HTTP endpoints (mod)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `http://localhost:47823/api/health` | tick count |
| GET | `http://localhost:47823/api/state` | game JSON |
| POST | `http://localhost:47823/api/command` | execute one command |

## Bridge endpoints (dashboard)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `http://localhost:3847/` | dashboard UI |
| POST | `http://localhost:3847/api/instruct` | player direct order → next tick |
| GET/POST/DELETE | `http://localhost:3847/api/memory` | session memory log |
