# as & at a cycle whose rider just got off
scoreboard players set @s mc.ridden 0
scoreboard players set @s mc.boost 0
scoreboard players set @s mc.skid 0
scoreboard players set @s mc.air 0
execute if score @s mc.fuel matches 1.. run playsound mastercycle:engine.stop neutral @a[distance=..48] ~ ~ ~ 0.9 1
execute if score @s mc.fuel matches 1.. run particle minecraft:end_rod ~ ~0.5 ~ 0.4 0.2 0.4 0.01 8
