# Positioned at the centre. Never twice in one place, never into unloaded chunks.
execute if entity @e[type=marker,tag=sunman_decayed,distance=..40] run return fail
execute unless loaded ~-16 ~ ~-16 run return fail
execute unless loaded ~16 ~ ~16 run return fail
execute unless loaded ~16 ~ ~-16 run return fail
execute unless loaded ~-16 ~ ~16 run return fail
function sunman:world/decay/run
return 1
