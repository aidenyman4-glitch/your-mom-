# Master Cycle — main loop (via #minecraft:tick)
scoreboard players add #tick mc.tmp 1
scoreboard players operation #t20 mc.tmp = #tick mc.tmp
scoreboard players operation #t20 mc.tmp %= #20 mc.const

execute as @a run function mastercycle:player/tick
execute as @e[type=item,tag=!mc.seen] at @s run function mastercycle:slate/check_drop
execute as @e[type=interaction,tag=mc.hitbox] at @s run function mastercycle:interact/hitbox
execute as @e[type=armor_stand,tag=mc.cycle] at @s run function mastercycle:cycle/tick

# Hitboxes whose cycle no longer exists (or is unloaded) are cleaned up;
# the cycle re-creates its hitbox when it comes back.
kill @e[type=interaction,tag=mc.hitbox,tag=!mc.synced]
tag @e[type=interaction,tag=mc.synced] remove mc.synced
