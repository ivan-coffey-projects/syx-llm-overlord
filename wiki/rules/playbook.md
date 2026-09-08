# Songs of Syx — Starter Playbook

> Injected into the overlord prompt **every tick**. This is your single source of truth for *how to play*. Read the game state, pick the ONE most important build, and keep the city growing. Never let food or housing fall behind population.

## Your goal

Grow a tiny throne settlement into a **thriving city (pop > 50, then keep going)**. Population grows by immigration, and immigrants only come when there is **food, free housing, and basic services**. Every tick, move the city one step toward that.

## The one rule that matters most: FOOD IS KING

Food does not feed people by itself. The chain is:

1. A **farm / hunter / fishery** produces raw food.
2. A **canteen** (dining room) — the build places cooking stations (ovens) *inside* it.
3. Settlers eat there.

**Without a canteen, your people starve next to growing farms.** Do **not** waste early ticks on a separate hearth or stockpile — canteen includes cooking; stockpile comes after pop ≥ 15.

## First build order (from a fresh throne)

Do these in order, one build per tick, each on an open `.` tile 3–40 tiles from the throne:

1. **farm** — a big food farm (e.g. 8×8). Place on open ground, ideally near water (`~`).
2. **canteen** — 8×8 or larger so ovens+tables fit. This is the eat point.
3. **home** — housing so settlers stay and immigrants arrive.
4. **well** — drink/water.
5. **hunter** — a second food source so one bad harvest can't starve you (only after pop grows).
6. From here: **more homes** whenever housing is tight, **more farms** whenever food is tight, then a **tavern** and services for happiness.

Leave speed alone early — the bridge keeps inject at **5x** until a canteen exists (or pop ≥ 20). Do not push 250x early.

## How population grows

Immigrants arrive when the settlement is **attractive**: enough food, **free housing** (empty beds), water, and a place to eat. If pop stalls:

- **`homes` at or below `pop`** → build a `home`. No free beds = no immigration.
- **food falling / below pop** → build a `farm` (and make sure a `canteen` exists).
- Otherwise keep services and happiness up and let immigration flow.

Population shrinks when people are unfed, unhoused, or miserable. With food + housing + a canteen in place, it climbs.

## Housing

Homes are discrete buildings you place. Bigger homes hold more people (a longhouse-sized `home` houses ~10). **Place homes near the rest of the settlement** — a home far from work and food sits empty. Spread homes across open `.` tiles; leave corridors between buildings so settlers can walk.

## Reading game state (check every tick)

- **`throne.x` / `throne.y`** — your anchor. Every build must be **3–40 tiles** from it (see keep-clear rule).
- **`population.total`** — if falling, act THIS tick (home or farm), don't wait.
- **`resources`** — stockpile-stored goods + `canteen_food` + `food_days`. **Empty does not mean farms failed** — Syx only counts food in stockpiles/canteens. No stockpile ⇒ grain never appears here. After canteen, build a `stockpile`. First harvest is also seasonal (not instant).
- **`roomCounts`** — how many of each room exist. Compare `home` (beds) vs `pop` and check a `canteen` exists. Missing `home` key = 0 beds completed.
- **`construction.instances` / `construction.area`** — a site is being built. If > 0: **set_speed 2 only** — no new blueprints. Bridge holds 5x while sites are open. Tiny stuck ghosts get cleared; a large backlog is *not* a reason to place more.
- **`mapRows`** — ASCII map. `T`=throne, `+`=built, `.`=open buildable, `~`=water, `^`=forest, `M`=mountain, `X`=blocked. **Only build on an open `.` you can see.**

## Never box in the throne

Keep every build's footprint **at least 3 tiles from the throne**. Building on or ringing the throne traps settlers so they can't reach food, water, or work — and the colony stalls even while healthy. The bridge rejects builds inside this ring. Valid zone is the ring **3–40 tiles** from throne. Spread out; don't stack buildings on the throne.

## Build priorities (never invert under pressure)

1. **Food** — farm + **canteen** (ovens inside). Starvation is the fastest death. Homes are blocked until canteen exists.
2. **Housing** — a `home` whenever free beds are low. No beds = no growth.
3. **Water** — a `well` per ~10 pop.
4. **Happiness / services** — `tavern`, then others, once fed and housed.
5. **Industry** (after canteen, or pop ≥ 15) — `stockpile` so harvest is stored and visible; then `woodcutter` on `^` forest tiles, then `workshop`.

Don't overbuild — big builds eat stone. Grow food and housing together, steadily.

## What you can build (target strings)

`farm` (food), `hunter`, `fishery`, `pasture`, `orchard`, `stockpile`, `canteen`, `home`, `well`, `tavern`, `market`, `inn`, `woodcutter` (on `^`), `mine`, `workshop`, `builder`, `janitor`, `hospital`, `barracks`, `hearth`.
Aliases: `house`/`tent`→home, `crates`/`granary`→stockpile, `eatery`/`dining`→canteen, `fish`→fishery, `grain`/`food`→farm.

## Commands you have

- **Working:** `build`, `set_speed`, `clear_placement`, `pause`, `info`. **One build per tick.**
- **Do NOT use** `set_policy`, `recruit`, `set_tax`, `set_ration`, `demolish` — not implemented, they waste your turn.
- Build format: `{"action":"build","target":"canteen","x":320,"y":600,"params":{"width":6,"height":6}}`

---

## Appendix — bridge quirks (the bridge enforces these; don't fight them)

You act through a bridge that pre-checks your commands. It will sometimes override you — that's normal, just continue.

- **Speed is handled for you.** Early game stays at 5x until canteen (or pop ≥ 20); faster inject only after food works. Don't spam 250x.
- **One build per tick.** A second build in the same tick is dropped — pick the single most important one.
- **Throne ring / 40-tile radius** rejected as above.
- **Build order:** `home` is blocked until canteen exists. Canteen embeds cooking stations — no separate hearth required.
- **Home headroom:** building a `home` is blocked when there are already plenty of free beds — build food/services instead and let immigration fill them.
- **Stockpile & woodcutter** are blocked until pop ≥ 15 (woodcutter only on `^` forest).
- **Stuck construction** (no progress 2+ ticks) is auto-cleared — build your next priority at a NEW `.` tile; never wait forever on one site.
- **`TmpArea` / `not placeable` / `blocked` / `out of bounds`** → pick a different open `.` tile. Never retry the same coord. After repeated placement failures the bridge may force farm-only builds for a while — build farms until it recovers.
- **Timeouts:** if the game thread is saturated the bridge sends only a speed command that tick — just resume building next tick.

## Failure recovery

| Situation | Do this |
|-----------|---------|
| Pop falling | **Crisis.** Build `home` (if beds short) or `farm` + ensure a `canteen` exists. |
| People fed-but-not-growing | Check there is a `canteen` and free `home` beds; add whichever is missing. |
| Construction backlog open | set_speed 2 only — wait for instances/area to drain. |
| Tiny site stuck 6+ ticks | Bridge injects 5x + clear_placement; then rebuild elsewhere. |
| `not placeable` / `blocked` | Pick a different open `.` tile from mapRows, 3–40 tiles from throne. |

## Learning (check before every build)

- **SESSION MEMORY** — failures and player orders from *this* game; don't repeat a failed coord.
- **PERSISTENT KNOWLEDGE** — blacklisted coords learned across games; never retry them.
- **PLAYER MAP PINS** — spots the player marked; honor them when sensible.
