# Once a second.
schedule function sunman:slow 20t replace
# the decal cap: past 512 blood decals, the ones furthest from a player go first
execute store result score #sm sm.decals if entity @e[type=item_display,tag=sm_decal]
execute if score #sm sm.decals matches 513.. as @r at @s run kill @e[type=item_display,tag=sm_decal,sort=furthest,limit=16]
# the abandoned village: a player near living villagers who know where their bell is
execute if score #sm sm.decay matches 1.. as @a[gamemode=!spectator] at @s if entity @e[type=villager,distance=..56] run function sunman:world/try_decay
# a decay job whose chunks were unloaded mid-way picks up again when they load
execute if entity @e[type=marker,tag=sm_decay_job] run schedule function sunman:world/decay/job 1t replace
# and what a dead village sounds like
execute as @a[gamemode=!spectator] at @s if entity @e[type=marker,tag=sunman_decayed,distance=..36] run function sunman:world/ambience
