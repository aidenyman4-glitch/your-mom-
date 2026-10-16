# as each player
execute unless score @s mc.id matches 1.. run function mastercycle:player/assign_id
execute if score @s mc.cd matches 1.. run scoreboard players remove @s mc.cd 1
execute if score @s mc.use matches 1.. at @s run function mastercycle:slate/use
