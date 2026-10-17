# as & at a cycle that just rammed something
playsound mastercycle:impact.ram neutral @a[distance=..48] ~ ~ ~ 1 1
execute rotated as @s run particle minecraft:crit ^ ^0.8 ^1.6 0.35 0.35 0.35 0.3 12
execute rotated as @s run particle minecraft:electric_spark ^ ^0.8 ^1.6 0.3 0.3 0.3 0.4 8
scoreboard players operation @s mc.speed -= #10 mc.const
