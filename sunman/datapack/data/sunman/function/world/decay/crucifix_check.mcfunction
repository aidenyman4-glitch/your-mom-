execute store result score #sm sm.head run data get entity @s Pos[1]
scoreboard players operation #sm sm.head -= #sm sm.cy
execute unless score #sm sm.head matches 4.. run return fail
# on a house, not over the bell itself
execute if entity @e[type=marker,tag=sm_decay_job,distance=..6] run return fail
execute unless block ~ ~ ~ #minecraft:air run return fail
execute unless block ~ ~1 ~ #minecraft:air run return fail
execute unless block ~ ~-1 ~ #sunman:smashable unless block ~ ~-1 ~ #sunman:solid run return fail
# facing the bell, so it is the first thing you see from the middle of the village
execute facing entity @e[type=marker,tag=sm_decay_job,limit=1,sort=nearest] feet run summon item_display ~ ~ ~ {Tags:["sunman_corpse","sunman_crucified","sm_new"],item:{id:"minecraft:paper",count:1,components:{"minecraft:item_model":"sunman:crucified_villager"}},item_display:"fixed",view_range:3.0f,shadow_radius:0f,transformation:{left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f],translation:[0f,0f,0f],scale:[3f,3f,3f]}}
execute facing entity @e[type=marker,tag=sm_decay_job,limit=1,sort=nearest] feet as @e[type=item_display,tag=sm_new] run tp @s ~ ~ ~ ~ 0
tag @e[type=item_display,tag=sm_new] remove sm_new
scoreboard players set #sm sm.ok 1
return 1
