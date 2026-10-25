# One blood decal on the ground under the executor.
summon marker ~ ~1 ~ {Tags:["sm_probe"]}
scoreboard players set #sm sm.probe 0
execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s run function sunman:util/ground
execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s if block ~ ~ ~ #sunman:see_through unless block ~ ~-1 ~ #sunman:see_through run function sunman:world/decay/decal_random
kill @e[type=marker,tag=sm_probe]
