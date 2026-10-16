# as & at a cycle that just ran into a wall
scoreboard players operation @s mc.speed /= #4 mc.const
playsound minecraft:item.shield.block neutral @a[distance=..48] ~ ~ ~ 0.7 0.6
execute rotated as @s run particle minecraft:crit ^ ^0.6 ^1.2 0.3 0.3 0.3 0.1 8
