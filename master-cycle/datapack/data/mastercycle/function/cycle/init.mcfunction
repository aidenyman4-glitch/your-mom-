# as a freshly summoned cycle, positioned & rotated like the summoning player
tag @s remove mc.new
tp @s ~ ~ ~ ~ 0
scoreboard players operation @s mc.owner = #me mc.id
scoreboard players operation @s mc.gen = #gen mc.tmp
scoreboard players operation @s mc.fuel = #fuel mc.tmp
scoreboard players set @s mc.speed 0
scoreboard players set @s mc.hum 0
scoreboard players set @s mc.jcd 0
scoreboard players set @s mc.boost 0
execute store result score @s mc.yaw run data get entity @s Rotation[0] 100
function mastercycle:math/wrap_yaw
scoreboard players add #next_cid mc.cid 1
scoreboard players operation @s mc.cid = #next_cid mc.cid
execute at @s run function mastercycle:cycle/spawn_hitbox
execute at @s run function mastercycle:fx/summon
