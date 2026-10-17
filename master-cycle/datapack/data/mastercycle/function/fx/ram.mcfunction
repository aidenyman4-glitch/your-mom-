# as & at a cycle that just rammed something
playsound minecraft:entity.player.attack.crit neutral @a[distance=..48] ~ ~ ~ 1 0.8
playsound minecraft:item.shield.block neutral @a[distance=..48] ~ ~ ~ 0.5 0.7
execute rotated as @s run particle minecraft:crit ^ ^0.8 ^1.6 0.35 0.35 0.35 0.3 12
execute rotated as @s run particle minecraft:electric_spark ^ ^0.8 ^1.6 0.3 0.3 0.3 0.4 8
scoreboard players operation @s mc.speed -= #10 mc.const
