$execute positioned ~$(bx) ~8 ~$(bz) summon marker run tag @s add sm_probe
scoreboard players set #sm sm.probe 0
execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s run function sunman:util/ground
scoreboard players set #sm sm.ok 0
execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s if block ~ ~ ~ #sunman:see_through unless block ~ ~-1 ~ #sunman:see_through run function sunman:world/decay/gore with storage sunman:village p
kill @e[type=marker,tag=sm_probe]
execute if score #sm sm.ok matches 1 run return 1
return fail
