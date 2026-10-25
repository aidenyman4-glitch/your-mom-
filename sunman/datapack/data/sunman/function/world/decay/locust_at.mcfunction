$execute positioned ~$(bx) ~$(by) ~$(bz) summon marker run tag @s add sm_probe
scoreboard players set #sm sm.probe 0
execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s run function sunman:util/ground
scoreboard players set #sm sm.ok 0
execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s align xyz positioned ~0.5 ~ ~0.5 unless entity @e[type=interaction,tag=sunman_locust,distance=..4] if function sunman:util/roofed run function sunman:world/decay/locust_spot
kill @e[type=marker,tag=sm_probe]
execute if score #sm sm.ok matches 1 run return 1
return fail
