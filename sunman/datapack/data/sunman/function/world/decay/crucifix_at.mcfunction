# From high above down onto whatever is there; it has to be a roof, four blocks up or more.
$execute positioned ~$(bx) ~16 ~$(bz) summon marker run tag @s add sm_probe
scoreboard players set #sm sm.probe 0
execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s run function sunman:util/ground
scoreboard players set #sm sm.ok 0
execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s run function sunman:world/decay/crucifix_check
kill @e[type=marker,tag=sm_probe]
execute if score #sm sm.ok matches 1 run return 1
return fail
