# as & at a cycle whose rider jumped (on the ground, or within coyote time)
scoreboard players set #hop mc.tmp 1
scoreboard players set @s mc.jcd 8
scoreboard players set @s mc.coyote 0
scoreboard players set @s mc.jbuf 0
scoreboard players operation #burn mc.tmp += #cfg.jump_burn mc.const
scoreboard players operation #jvel mc.tmp = #cfg.jump mc.const
execute if score #boosting mc.tmp matches 1 run scoreboard players operation #jvel mc.tmp = #cfg.jump_boost mc.const
playsound minecraft:entity.breeze.jump neutral @a[distance=..48] ~ ~ ~ 0.9 1.25
playsound mastercycle:engine.boost neutral @a[distance=..48] ~ ~ ~ 0.35 1.6
particle minecraft:end_rod ~ ~0.2 ~ 0.4 0.05 0.4 0.03 14
execute rotated as @s run particle minecraft:electric_spark ^ ^0.15 ^0.9 0.2 0.02 0.2 0.3 5
execute rotated as @s run particle minecraft:electric_spark ^ ^0.15 ^-0.4 0.2 0.02 0.2 0.3 5
