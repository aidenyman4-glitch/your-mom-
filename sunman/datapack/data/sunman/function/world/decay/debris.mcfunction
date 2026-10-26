# A breach: mark it. What came out of the wall is laid on the floor below it once all
# the ruin is done (stage 3), so a later breach cannot pull the floor out from under it.
function sunman:util/roll
execute if score #sm sm.rng matches ..69 run summon marker ~ ~ ~ {Tags:["sm_debris_spot"]}
