$execute positioned ~$(bx) ~8 ~$(bz) summon marker run tag @s add sm_probe
scoreboard players set #sm sm.probe 0
execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s run function sunman:util/ground
execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s if block ~ ~ ~ #minecraft:air if block ~ ~-1 ~ #sunman:dead_ground run function sunman:world/decay/tuft with storage sunman:village p
kill @e[type=marker,tag=sm_probe]
