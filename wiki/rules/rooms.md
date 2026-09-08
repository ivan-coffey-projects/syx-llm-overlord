# Room types & aliases

Resolved by `RoomResolver.java` in the mod. Use these `target` strings in build commands.

## Common aliases

| You say | Game room |
|---------|-----------|
| home, house, housing, tent, shelter | HOME |
| stockpile, crates, granary | STOCKPILE |
| well | first WELLS blueprint |
| farm | first FARMS blueprint |
| pasture | first PASTURES |
| woodcutter | WOOD_CUTTER |
| fishery, fish | first FISHERIES |
| hunter | first HUNTERS |
| orchard | first ORCHARDS |
| mine | first MINES |
| tavern | first TAVERNS |
| barracks | first BARRACKS |
| export, import, hauler, transport | logistics rooms |

## Indoor vs outdoor

- **Indoor area** (needs cleared indoor tiles): home, stockpile
- **Outdoor area** (params width/height): farm, pasture, orchard
- **Outdoor single tile**: well, woodcutter, fishery, hunter

## Placement tips

- Anchor all coordinates to [throne position](playbook#Core facts.md) ±40 tiles.
- Area rooms: spiral search relocates automatically if direct spot fails.
- Single-item rooms (well): one attempt only — no spiral (TmpArea safety).
