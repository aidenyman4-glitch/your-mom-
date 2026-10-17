# as & at a cycle sitting in water: climb to the surface, then ride on it
# (deep = water at head height too; surface = water at the hull only)
execute if block ~ ~1.0 ~ minecraft:water run data modify storage mastercycle:tmp m[1] set value 0.14d
execute unless block ~ ~1.0 ~ minecraft:water run data modify storage mastercycle:tmp m[1] set value 0.0d
scoreboard players set #inliquid mc.tmp 1
