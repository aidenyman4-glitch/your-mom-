# as a ridden cycle: turn toward the rider's view, at most #rate per tick.
# A / D aim 45 degrees left / right of the view for carving without the mouse.
execute on passengers if entity @s[type=player] store result score #look mc.tmp run data get entity @s Rotation[0] 100
execute if score #left mc.tmp matches 1 unless score #right mc.tmp matches 1 run scoreboard players remove #look mc.tmp 4500
execute if score #right mc.tmp matches 1 unless score #left mc.tmp matches 1 run scoreboard players add #look mc.tmp 4500
# parked and no throttle: looking around doesn't swing the bike
execute if score @s mc.speed matches -29..29 unless score #fwd mc.tmp matches 1 unless score #back mc.tmp matches 1 run return 0

# signed shortest angle from the bike's heading to the view, in (-180, 180]
scoreboard players operation #diff mc.tmp = #look mc.tmp
scoreboard players operation #diff mc.tmp -= @s mc.yaw
scoreboard players operation #diff mc.tmp %= #36000 mc.const
execute if score #diff mc.tmp matches ..-1 run scoreboard players add #diff mc.tmp 36000
execute if score #diff mc.tmp matches 18001.. run scoreboard players remove #diff mc.tmp 36000
execute if score #diff mc.tmp matches 0 run return 0

scoreboard players operation #rate mc.tmp = #cfg.turn mc.const
execute if score @s mc.speed matches -40..40 run scoreboard players operation #rate mc.tmp = #cfg.turn_slow mc.const
execute if score #boosting mc.tmp matches 1 run scoreboard players operation #rate mc.tmp = #cfg.turn_boost mc.const
# clamp the turn to +-#rate
scoreboard players operation #neg mc.tmp = #rate mc.tmp
scoreboard players operation #neg mc.tmp *= #-1 mc.const
execute if score #diff mc.tmp > #rate mc.tmp run scoreboard players operation #diff mc.tmp = #rate mc.tmp
execute if score #diff mc.tmp < #neg mc.tmp run scoreboard players operation #diff mc.tmp = #neg mc.tmp
scoreboard players operation @s mc.yaw += #diff mc.tmp
function mastercycle:math/wrap_yaw
execute store result entity @s Rotation[0] float 0.01 run scoreboard players get @s mc.yaw
