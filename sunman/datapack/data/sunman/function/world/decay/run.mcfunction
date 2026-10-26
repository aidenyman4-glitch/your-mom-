# The transform. The decayed marker goes down FIRST: if anything cuts this short, the
# place is still never decayed twice. The blocks change now; the rest is staged over the
# next ticks by a job marker, so no single tick runs more than a third of
# max_command_sequence_length however awkward the village.
summon marker ~ ~ ~ {Tags:["sunman_decayed"]}
function sunman:world/decay/light
function sunman:world/decay/fabric
function sunman:world/decay/stone
function sunman:world/decay/fields
function sunman:world/decay/doors
# the villagers are gone, and their bodies will be here instead
execute as @e[type=villager,distance=..48] at @s run function sunman:world/decay/vanish
execute as @e[type=iron_golem,distance=..48] at @s run function sunman:world/decay/vanish_golem
summon marker ~ ~ ~ {Tags:["sm_decay_job","sm_new"]}
scoreboard players set @e[type=marker,tag=sm_new,tag=sm_decay_job] sm.stage 2
tag @e[type=marker,tag=sm_new] remove sm_new
schedule function sunman:world/decay/job 1t replace
