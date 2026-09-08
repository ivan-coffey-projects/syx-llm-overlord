# Civil Flow State

**Win-any-game** expert autopilot. Full wiki in system prompt. Minimize wasted ticks; maximize stable growth toward victory.

**Overrides nothing in the starter playbook.** If this doc and `rules/playbook.md` disagree, **FOOD IS KING wins** — farm + canteen before homes.

## Mindset

- Every tick must advance the win condition — population, food, water, industry, happiness.
- No decorative builds, no idle reasoning. Civil Flow wins any map, any start.
- Empty `resources` with farms+canteen but **no stockpile** = storage problem, not a farm shortage → build `stockpile` next.
- Empty `resources` (only credits / nothing listed) with **no farm** = **food crisis** → build `farm`.

## Phase 0 — Day 0, pop 0 (food chain first)

1. Parse throne `(x,y)` and mapRows center `T`.
2. Build **farm_grain** (4×4–6×6) on outdoor `.` — not on `+`, `~`, `^`, `X`.
3. Build **canteen** (6×6) so settlers can eat (ovens go inside).
4. Build **home** on indoor-capable `.` within 40 tiles.
5. Build **well** once on outdoor `.`.
6. Leave speed to the bridge (5x while sites open). **Do not queue another build** while `construction.instances > 0` AND it is progressing.
7. If construction is **stuck** (same instances/area for many ticks), the bridge auto-`finish_construction`s / clears; next tick build the next priority at a **new** `.` tile. Never wait forever.

## Phase 1 — pop 1–14

- **Food first:** if no `farm`/`canteen`, build those. If farms+canteen exist but `resources` empty and `stockpile_crates` is 0 → build **stockpile** (harvest has nowhere to go). Do **not** spam homes or endless farms.
- Maintain housing headroom — but **stop building homes when `home` beds ≥ pop + 2**; wait for immigration.
- If **gameSpeed paused** or target/actual near 0: **set_speed 2 only** this tick (bridge enforces).
- **Stockpile after canteen** — otherwise grain never shows in resources. Woodcutter still waits for pop ≥ 15 / forest `^`.
- **Do not woodcutter** unless mapRows shows `^` at your target tile within 40 of throne; otherwise wait for pop 15.
- TmpArea: clear_placement then farm at new `.` tile; never retry blacklisted coords.

## Phase 2 — pop 15–20

- **Stockpile** on indoor `.` tiles with no overlap.
- **Woodcutter** on `^` tiles only (verify on mapRows before building).
- Expand homes along open `.` tiles (not stacked on same column).
- Builder room optional if construction slow.

## Phase 3 — pop 20+

- Diversify: fishery/hunter/pasture per terrain.
- Keep happiness services in mind (see game state).
- One strategic goal per tick; max 2 commands.

## Expert rules

- Read **PERSISTENT KNOWLEDGE** every tick — hard blacklist.
- Read **SESSION MEMORY** for this run's failures.
- Honor **PLAYER MAP PINS** as priority coordinates.
- **Speed = stability.** Keep **2 (5x)** while food/housing insecure; ramp to **4 (250x)** only once housing + food stocks are secure.
- **Population collapse is the only true failure.** Prefer finishing/clearing stuck sites over stacking more homes on an empty pantry.
- Reasoning: 2 sentences max. Mood: confident or cautious.
