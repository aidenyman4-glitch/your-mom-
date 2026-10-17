# Removes every Master Cycle and all scoreboards. Disable the data pack afterwards
# (/datapack disable "file/<pack name>") or it will set itself up again on /reload.
execute as @e[type=armor_stand,tag=mc.cycle] run function mastercycle:cycle/despawn
kill @e[type=interaction,tag=mc.hitbox]
tag @a remove mc.welcomed
scoreboard objectives remove mc.fuel
scoreboard objectives remove mc.speed
scoreboard objectives remove mc.yaw
scoreboard objectives remove mc.cid
scoreboard objectives remove mc.owner
scoreboard objectives remove mc.gen
scoreboard objectives remove mc.hum
scoreboard objectives remove mc.jcd
scoreboard objectives remove mc.boost
scoreboard objectives remove mc.ridden
scoreboard objectives remove mc.air
scoreboard objectives remove mc.low
scoreboard objectives remove mc.skid
scoreboard objectives remove mc.lost
scoreboard objectives remove mc.death
scoreboard objectives remove mc.jbuf
scoreboard objectives remove mc.coyote
scoreboard objectives remove mc.id
scoreboard objectives remove mc.stored
scoreboard objectives remove mc.cd
scoreboard objectives remove mc.use
scoreboard objectives remove mc.tmp
scoreboard objectives remove mc.const
data remove storage mastercycle:tmp m
data remove storage mastercycle:tmp hum
data remove storage mastercycle:hud bar
tellraw @s {"text":"Master Cycle uninstalled. Now disable the data pack with /datapack disable.","color":"aqua"}
