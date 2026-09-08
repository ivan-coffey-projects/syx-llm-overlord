"""Shared map / build radius — keep in sync with MapExporter.DEFAULT_RADIUS in the mod."""

MAP_RADIUS = 40
MAX_THRONE_DISTANCE = MAP_RADIUS

# Keep-clear ring around the throne. Builds whose footprint comes within this
# many tiles of the throne are rejected: boxing the throne in traps settlers
# (they can't path to it or out to food/water), which stalls/kills the colony
# even with the NO-DIE health boosts active. Leaves an access corridor open.
MIN_THRONE_CLEARANCE = 3
