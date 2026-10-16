# as a cycle: #turn is -1 (A, left) or 1 (D, right)
scoreboard players operation #rate mc.tmp = #cfg.turn mc.const
execute if score @s mc.speed matches -40..40 run scoreboard players operation #rate mc.tmp = #cfg.turn_slow mc.const
execute if score #boosting mc.tmp matches 1 run scoreboard players operation #rate mc.tmp = #cfg.turn_boost mc.const
scoreboard players operation #rate mc.tmp *= #turn mc.tmp
scoreboard players operation @s mc.yaw += #rate mc.tmp
function mastercycle:math/wrap_yaw
execute store result entity @s Rotation[0] float 0.01 run scoreboard players get @s mc.yaw
# swing the rider's camera round with the bike, like a boat
execute store result storage mastercycle:tmp turn.d float 0.01 run scoreboard players get #rate mc.tmp
execute on passengers if entity @s[type=player] run function mastercycle:drive/turn_camera with storage mastercycle:tmp turn
