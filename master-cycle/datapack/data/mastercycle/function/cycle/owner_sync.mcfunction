# as & at a cycle, once a second
scoreboard players operation #o mc.tmp = @s mc.owner
scoreboard players operation #g mc.tmp = @s mc.gen
scoreboard players operation #f mc.tmp = @s mc.fuel
scoreboard players set #stale mc.tmp 0
execute as @a if score @s mc.id = #o mc.tmp run function mastercycle:cycle/owner_sync_player
execute if score #stale mc.tmp matches 1 run function mastercycle:cycle/dismiss
