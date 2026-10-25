"""Material colours for the two tier creatures, and the grade the tape is shot through.

The shipped atlas has a real bug: export_models.py resolves a cube's material with
`SLOTS.get(mat, SLOTS["bone"])`, and SLOTS never had entries for the `lc_*` / `dw_*`
materials tiers.py authors. So every tier-creature cube landed on the Sun Man's bone tile
and the creatures came out the same dead grey as him. The sheet is explicit that the Locust
is greyscale, pale blue-grey, four tones.

These are those tones. They colour the renders here, and `atlas_patch.py` paints them into
the atlas's free quadrant so the exported models finally resolve to them in game.
"""

LOCUST = {
    "lc_light": (178, 188, 193),      # the big head, the finger bones — chalk with a blue cast
    "lc_mid":   (131, 141, 147),      # thorax and limb segments
    "lc_dark":  (74, 82, 88),         # neck, feet, the hand knuckle
    "lc_joint": (102, 111, 117),      # the exposed blocky joints and the spine ridge
    "lc_void":  (6, 7, 9),            # eye sockets and mouth: holes, not features
}

# Tier 2. Built from Aiden's five references: a silhouette in every one of them, so the
# body is barely lighter than the night it stands in and the only real colour in the
# creature is the pair of eyes.
# The body is a cold mid grey, not black, and that is the reading that satisfies all five
# references at once: backlit against a pale sky it is a pure silhouette (the hilltop and
# the ink drawing), and caught in a headlight at night it is the pale thing in the road.
# A black body could never do the second. The hat stays black in every light.
DARK_WALKER = {
    "dw_dark":  (84, 87, 95),         # torso, head, the long bones of the limbs
    "dw_mid":   (104, 107, 116),      # limb segments, so the taper still reads at distance
    "dw_hat":   (17, 17, 21),         # brim and crown: the one thing that is black in any light
    "dw_pale":  (146, 149, 158),      # joint knobs and the tips of the tendrils
    "dw_eye":   (255, 243, 196),      # light_emission 15
}

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
