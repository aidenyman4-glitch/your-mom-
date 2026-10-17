# as & at a cycle in lava: it floats, but the heat eats fuel and the rider
# needs the hull's shielding to survive the crossing
execute if block ~ ~1.0 ~ minecraft:lava run data modify storage mastercycle:tmp m[1] set value 0.10d
execute unless block ~ ~1.0 ~ minecraft:lava run data modify storage mastercycle:tmp m[1] set value 0.0d
scoreboard players set #inliquid mc.tmp 1
scoreboard players operation @s mc.fuel -= #cfg.lava_burn mc.const
execute if score @s mc.fuel matches ..0 run scoreboard players set @s mc.fuel 0
execute on passengers if entity @s[type=player] run effect give @s minecraft:fire_resistance 2 0 true
execute if score #t20 mc.tmp matches 0 run particle minecraft:large_smoke ~ ~0.3 ~ 0.4 0.1 0.4 0.01 6
