# as & at every Master Cycle, every tick

# keep the click hitbox glued to the cycle (it sits slightly forward, over the body)
scoreboard players operation #cid mc.tmp = @s mc.cid
scoreboard players set #found mc.tmp 0
execute rotated as @s positioned ^ ^ ^0.5 as @e[type=interaction,tag=mc.hitbox,distance=..10] if score @s mc.cid = #cid mc.tmp run function mastercycle:cycle/sync_hitbox
execute if score #found mc.tmp matches 0 run function mastercycle:cycle/spawn_hitbox

# ridden: read WASD and drive. Empty but still rolling: coast to a stop.
execute if predicate mastercycle:has_rider run function mastercycle:drive/tick
execute unless predicate mastercycle:has_rider if score @s mc.ridden matches 1 run function mastercycle:fx/dismount
execute unless predicate mastercycle:has_rider unless score @s mc.speed matches 0 run function mastercycle:drive/coast_unridden
# parked with fuel: the hubs pulse faintly every 2 seconds
execute if score #t40 mc.tmp matches 0 unless predicate mastercycle:has_rider if score @s mc.fuel matches 1.. run function mastercycle:fx/idle

# once a second: mirror fuel to the owner, and remove stale duplicates
execute if score #t20 mc.tmp matches 0 run function mastercycle:cycle/owner_sync
