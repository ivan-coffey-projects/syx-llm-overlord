# Failure messages

What build errors mean and what to do next.

| Message | Meaning | Fix |
|---------|---------|-----|
| `not placeable` / `blocked` | Tile invalid for that room type | Try adjacent tile; switch indoor↔outdoor |
| `Must not be placed on room` | Overlapping existing room | Offset coordinates; check memory for what’s built |
| `insufficient: Crates` (stockpile) | Stockpile blueprint needs crate items in shape | Different indoor spot; build home first |
| `Out of bounds` | x/y outside map | Use throne-relative coords |
| `Unknown room type` | Bad target string | See [rooms](rooms.md) |
| `Command timed out waiting for game thread` | Game updater blocked (often TmpArea) | One command next tick; restart game if repeated |
| `In use by: PlacerItemSingle` (game crash) | Stale placement lock | Fixed in mod — restart if on old JAR |

Failures are duplicated as `[failure]` entries in [memory log](../memory/log-format.md).
