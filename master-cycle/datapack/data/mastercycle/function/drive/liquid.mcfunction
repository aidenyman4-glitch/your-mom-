# as & at any cycle, every tick: float on water or lava instead of sinking.
# Runs after the driving physics, so it has the last word on vertical motion -
# except on the tick of a jump, which is allowed to launch out of the water.
scoreboard players set #wet mc.tmp 0
execute if block ~ ~0.1 ~ minecraft:water run function mastercycle:drive/float_water
execute if block ~ ~0.1 ~ minecraft:lava run function mastercycle:drive/float_lava
# just went in: splash
execute if score #wet mc.tmp matches 1 unless score @s mc.wet matches 1 run function mastercycle:fx/splash
execute if score #wet mc.tmp matches 2 unless score @s mc.wet matches 2 run function mastercycle:fx/splash
# lava keeps hissing while you ride it
execute if score #wet mc.tmp matches 2 if score #t20 mc.tmp matches 0 run playsound mastercycle:liquid.sizzle neutral @a[distance=..48] ~ ~ ~ 0.8 1
scoreboard players operation @s mc.wet = #wet mc.tmp
