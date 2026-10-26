# 2 to 4 Locusts, standing frozen against the inside walls of the houses.
execute store result score #sm sm.n run random value 2..4
scoreboard players set #sm sm.i 0
scoreboard players set #sm sm.try 400
function sunman:world/decay/locust_search
