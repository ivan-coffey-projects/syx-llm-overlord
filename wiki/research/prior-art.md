# Prior art & related work

## Has anyone done *this* before?

**Not exactly.** As of mid-2026 there is no public "LLM plays Songs of Syx autonomously" mod, Steam Workshop entry, or GitHub project matching this stack (Java mod HTTP API → Python bridge → LLM tick loop → room placement).

### What exists for Songs of Syx

| Work | What it is | Link |
|------|------------|------|
| **Arg0n mod example** | Official-style Java mod toolchain, docs, Maven pipeline | [github.com/4rg0n/songs-of-syx-mod-example](https://github.com/4rg0n/songs-of-syx-mod-example) |
| **SoS modding docs** | Wiki + readthedocs; Java mods, no external AI API | [songsofsyx.com/wiki/Modding](https://songsofsyx.com/wiki/index.php/Modding) |
| **Community mods** | Content, balance, races, UI — not LLM agents | Steam Workshop / songsofsyx.com mods |
| **Citizen AI** | Built-in `settlement.entity.humanoid.ai` — citizens, not an LLM overlord | Game source (`SongsOfSyx-sources.jar`) |

SoS is **not** designed for external control. Arg0n's docs recommend encapsulation + reflection to touch game internals — which is exactly what this project does for room placement.

### Closest cousins (other games)

| Game | Pattern |
|------|---------|
| **Screeps** | You write JS; bot runs 24/7 against players — native API |
| **Bitburner** | LLM-friendly: automate via in-game terminal API |
| **Factorio + scripts** | Circuit/logistics automation, not LLM |
| **OpenAI Gym / custom envs** | Research wrappers, not shipped games |

Your vault already catalogued LLM-ready games in `programming-games-llm-targets.md` — SoS was **Tier 2: needs wrapper**, which is this project.

### What makes this project novel

1. **In-process mod** exposing settlement state + build commands on localhost
2. **LLM bridge** with playbook + persistent session memory
3. **Obsidian wiki** as editable rules source (this wiki)
4. **Real room placement** via game's `RoomPlacer` API (not fake "queued" builds)

### If you find something similar

Add links here — Steam discussions, Reddit, Discord `#modding`, GitHub search terms:
`songs-of-syx`, `songsofsyx`, `llm`, `automation`, `agent`
