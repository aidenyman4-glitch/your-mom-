# 3.7: 4 to 8 bodies, inside the houses first, then round them; and pieces of others.
execute store result score #sm sm.n run random value 4..8
scoreboard players set #sm sm.i 0
scoreboard players set #sm sm.try 80
function sunman:world/decay/corpse_search
scoreboard players set #sm sm.i 0
scoreboard players set #sm sm.n 3
scoreboard players set #sm sm.try 40
function sunman:world/decay/gore_search
