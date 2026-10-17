# as a cycle: turn speed + heading into the armor stand's Motion.
# The game then moves it with real collision, gravity and step-up.

# Sense walls past the nose (or the tail when reversing) BEFORE moving. The
# armor stand's own collision box is tiny and sits mid-bike, so without this
# the model's nose would slide ~1.5 blocks into a wall before anything stops it.
execute if score @s mc.speed matches 1.. run function mastercycle:drive/sense_front
execute if score @s mc.speed matches ..-1 run function mastercycle:drive/sense_rear

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
# the hull floats: rise while submerged, hover once at the surface
execute if block ~ ~0.1 ~ minecraft:water run function mastercycle:drive/float_water
execute if block ~ ~0.1 ~ minecraft:lava run function mastercycle:drive/float_lava
execute if score #hop mc.tmp matches 1 store result storage mastercycle:tmp m[1] double 0.001 run scoreboard players get #jvel mc.tmp
data modify entity @s Motion set from storage mastercycle:tmp m
