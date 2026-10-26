# 3.7: the bodies, and the pieces of others
function sunman:world/decay/corpses
# the golem, dead where it stood (or somewhere in the open, if the village had none)
scoreboard players set #sm sm.i 0
scoreboard players set #sm sm.try 60
execute unless entity @e[type=marker,tag=sm_golem_spot,distance=..64] run function sunman:world/decay/golem_spot_search
execute as @e[type=marker,tag=sm_golem_spot,distance=..64] at @s run function sunman:world/decay/dead_golem
kill @e[type=marker,tag=sm_golem_spot,distance=..64]
# and one of them nailed up on a roof, facing the bell
execute store result score #sm sm.cy run data get entity @s Pos[1]
scoreboard players set #sm sm.i 0
scoreboard players set #sm sm.try 150
function sunman:world/decay/crucifix_search
