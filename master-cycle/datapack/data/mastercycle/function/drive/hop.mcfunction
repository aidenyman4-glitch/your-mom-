# as & at a grounded cycle whose rider pressed Space
scoreboard players set #hop mc.tmp 1
scoreboard players set @s mc.jcd 14
scoreboard players operation #burn mc.tmp += #cfg.jump_burn mc.const
playsound minecraft:entity.breeze.jump neutral @a[distance=..48] ~ ~ ~ 0.8 1.3
particle minecraft:end_rod ~ ~0.2 ~ 0.4 0.05 0.4 0.03 12
