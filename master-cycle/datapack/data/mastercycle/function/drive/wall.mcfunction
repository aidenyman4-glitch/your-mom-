# as & at a cycle about to hit a wall: stop dead (with a clunk if it was fast)
execute unless score @s mc.speed matches -149..149 run function mastercycle:drive/bump_fx
scoreboard players set @s mc.speed 0
