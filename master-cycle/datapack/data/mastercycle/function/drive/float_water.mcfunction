# as & at a cycle sitting in water: climb to the surface, then ride on it
# (deep = water at head height too; surface = water at the hull only)
scoreboard players set #wet mc.tmp 1
execute if block ~ ~1.0 ~ minecraft:water run data modify entity @s Motion[1] set value 0.14d
execute unless block ~ ~1.0 ~ minecraft:water run data modify entity @s Motion[1] set value 0.0d
