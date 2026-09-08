# Changelog

All notable changes to the Syx LLM Overlord project.

## [1.0.0] — Initial Release

### Working Features

- **Build rooms** — LLM can construct rooms (dormitories, farms, workshops, etc.) via the in-game API
- **Set game speed** — Control simulation speed (pause, 1x, 2x, 4x)
- **Pre-flight command guard** — Validates coordinates against throne position and map bounds before issuing commands
- **Coordinate blacklisting** — Tracks failed coordinates and avoids re-issuing doomed build orders
- **Session memory** — JSONL-backed persistent memory across ticks
- **Persistent knowledge** — Wiki-backed playbook injected into every LLM decision cycle
- **Map visualization** — Real-time settlement map grid in the dashboard
- **WebSocket dashboard** — Live dashboard at `http://localhost:3847` with chat, map, memory, and knowledge panels
- **Vision support** — LLM can request screenshots and interpret game visuals
- **Multiple personas** — `gregg` (balanced), `peace_god` (pacifist expansion), `tyrant` (aggressive growth)
- **Multiple game modes** — `civil_flow` (wiki-backed expert autopilot), `teacher` (teaches player while playing)

### Stubbed / Planned

The following commands are documented in the playbook but not yet implemented:

- `demolish` — Remove existing rooms
- `set_policy` — Adjust settlement policies
- `recruit` — Recruit new citizens
- `set_tax` — Modify tax rates
- `set_ration` — Adjust food rations

### Game Compatibility

- Songs of Syx **V69** (confirmed working)
- Auto-detects V69/V70 from installed mods during `install.sh`
