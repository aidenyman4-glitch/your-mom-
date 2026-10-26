"""Material colours for the two tier creatures, and the grade the tape is shot through.

The shipped atlas has a real bug: export_models.py resolves a cube's material with
`SLOTS.get(mat, SLOTS["bone"])`, and SLOTS never had entries for the `lc_*` / `dw_*`
materials tiers.py authors. So every tier-creature cube landed on the Sun Man's bone tile
and the creatures came out the same dead grey as him. The sheet is explicit that the Locust
is greyscale, pale blue-grey, four tones.

These are those tones. They colour the renders here, and `atlas_patch.py` paints them into
the atlas's free quadrant so the exported models finally resolve to them in game.
"""

# The tier creatures' materials are five-step ramps in `paint_tiers.RAMPS` (the skins are
# painted from them); flat renders use each ramp's base tone. The Locust is greyscale with a
# blue cast, four tones plus the black of its eyes. The Dark Walker is a cold mid grey, not
# black — backlit against a pale sky it is still a pure silhouette (the hilltop, the ink
# drawing), but caught in a headlight it is the pale thing in the road, which a black body
# could never be. The hat stays black in every light; the eyes are the only colour in it.
from paint_tiers import RAMPS  # noqa: E402

LOCUST = {k: v[2] for k, v in RAMPS.items() if k.startswith("lc_")}
DARK_WALKER = {k: v[2] for k, v in RAMPS.items() if k.startswith("dw_")}

MATS = {**LOCUST, **DARK_WALKER}

# ---------------------------------------------------------------- the grade
# Everything is shot as if recovered from tape, because that is what the mod does to the
# player's screen: fx/overlay_vhs is a real camera_overlay the datapack keeps equipped.

FOG = (16, 15, 19)                    # what distance dissolves into
GROUND = (28, 27, 31)
GROUND_FAR = (20, 19, 24)
SKY_LOW = (38, 35, 43)
SKY_HIGH = (15, 14, 19)
TREE = (26, 25, 31)
TREE_LIT = (35, 33, 40)
INK = (214, 210, 218)                 # burn-in text
REC = (158, 42, 42)
