# as a cycle: turn speed + heading into the armor stand's Motion.
# The game then moves it with real collision, gravity and step-up.

# heading in whole degrees -> sin / cos (x1000)
scoreboard players operation #a mc.tmp = @s mc.yaw
scoreboard players operation #a mc.tmp /= #100 mc.const
function mastercycle:math/sin
scoreboard players operation #sin mc.tmp = #r mc.tmp
scoreboard players add #a mc.tmp 90
execute if score #a mc.tmp matches 360.. run scoreboard players remove #a mc.tmp 360
function mastercycle:math/sin
scoreboard players operation #cos mc.tmp = #r mc.tmp

# start from the current motion so gravity / falling is kept
data modify storage mastercycle:tmp m set from entity @s Motion
execute unless score @s mc.speed matches -149..149 run function mastercycle:drive/check_bump

# Minecraft's facing vector is (-sin yaw, 0, cos yaw); speed is x1000, trig is x1000
scoreboard players operation #mx mc.tmp = #sin mc.tmp
scoreboard players operation #mx mc.tmp *= @s mc.speed
scoreboard players operation #mx mc.tmp *= #-1 mc.const
scoreboard players operation #mz mc.tmp = #cos mc.tmp
scoreboard players operation #mz mc.tmp *= @s mc.speed
execute store result storage mastercycle:tmp m[0] double 0.000001 run scoreboard players get #mx mc.tmp
execute store result storage mastercycle:tmp m[2] double 0.000001 run scoreboard players get #mz mc.tmp
execute if score #hop mc.tmp matches 1 run data modify storage mastercycle:tmp m[1] set value 0.48d
data modify entity @s Motion set from storage mastercycle:tmp m
