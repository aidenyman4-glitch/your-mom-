# as each player
execute unless score @s mc.id matches 1.. run function mastercycle:player/assign_id
# first time this player is seen: give them a Sheikah Slate and the controls
execute unless entity @s[tag=mc.welcomed] at @s run function mastercycle:player/welcome
execute if score @s mc.cd matches 1.. run scoreboard players remove @s mc.cd 1
execute if score @s mc.use matches 1.. at @s run function mastercycle:slate/use
