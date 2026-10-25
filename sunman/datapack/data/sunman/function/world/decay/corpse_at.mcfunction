$execute positioned ~$(bx) ~8 ~$(bz) summon marker run tag @s add sm_probe
scoreboard players set #sm sm.probe 0
execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s run function sunman:util/ground
scoreboard players set #sm sm.ok 0
# the first half of the tries take only spots under a roof: inside the houses
execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s if block ~ ~ ~ #sunman:see_through if block ~ ~1 ~ #sunman:see_through unless block ~ ~-1 ~ #sunman:see_through unless entity @e[type=item_display,tag=sunman_corpse,distance=..2.5] if score #sm sm.try matches 41.. run function sunman:world/decay/corpse_roofed with storage sunman:village p
execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s if block ~ ~ ~ #sunman:see_through if block ~ ~1 ~ #sunman:see_through unless block ~ ~-1 ~ #sunman:see_through unless entity @e[type=item_display,tag=sunman_corpse,distance=..2.5] if score #sm sm.try matches ..40 run function sunman:world/decay/corpse with storage sunman:village p
kill @e[type=marker,tag=sm_probe]
execute if score #sm sm.ok matches 1 run return 1
return fail
