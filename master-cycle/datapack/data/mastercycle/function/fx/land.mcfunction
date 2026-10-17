# as & at a ridden cycle touching down after being airborne
playsound mastercycle:impact.land neutral @a[distance=..48] ~ ~ ~ 1 1
particle minecraft:poof ~ ~0.1 ~ 0.5 0.02 0.5 0.02 8
execute rotated as @s run particle minecraft:electric_spark ^ ^0.1 ^0.9 0.15 0.02 0.15 0.2 4
execute rotated as @s run particle minecraft:electric_spark ^ ^0.1 ^-0.4 0.15 0.02 0.15 0.2 4
