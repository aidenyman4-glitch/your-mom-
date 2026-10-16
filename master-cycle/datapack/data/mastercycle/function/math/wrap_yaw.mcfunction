# as a cycle: keep mc.yaw (hundredths of a degree) within [0, 36000)
execute if score @s mc.yaw matches ..-1 run scoreboard players add @s mc.yaw 36000
execute if score @s mc.yaw matches 36000.. run scoreboard players remove @s mc.yaw 36000
