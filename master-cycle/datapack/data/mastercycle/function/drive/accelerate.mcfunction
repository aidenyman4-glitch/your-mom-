# as a cycle: throttle (W) is held and there is fuel
scoreboard players operation #max mc.tmp = #cfg.max_speed mc.const
scoreboard players operation #acc mc.tmp = #cfg.accel mc.const
scoreboard players set #burn mc.tmp 1
execute if score #boosting mc.tmp matches 1 run scoreboard players operation #max mc.tmp = #cfg.boost_speed mc.const
execute if score #boosting mc.tmp matches 1 run scoreboard players operation #acc mc.tmp = #cfg.boost_accel mc.const
execute if score #boosting mc.tmp matches 1 run scoreboard players operation #burn mc.tmp = #cfg.boost_burn mc.const
# rolling backwards: brake first
execute if score @s mc.speed matches ..-1 run scoreboard players operation @s mc.speed += #cfg.brake mc.const
# above the cap (a boost just ended): ease back down to cruising speed
execute if score @s mc.speed > #max mc.tmp run return run scoreboard players remove @s mc.speed 8
scoreboard players operation @s mc.speed += #acc mc.tmp
execute if score @s mc.speed > #max mc.tmp run scoreboard players operation @s mc.speed = #max mc.tmp
