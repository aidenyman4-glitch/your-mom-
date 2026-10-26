# webs strung under the ceilings of the rooms nobody uses
scoreboard players set #sm sm.i 0
scoreboard players set #sm sm.try 500
function sunman:world/decay/web_search
# the ground died where it stood: patches of dead earth, dead bushes
scoreboard players set #sm sm.i 0
scoreboard players set #sm sm.n 22
function sunman:world/decay/blight_loop
# the broken wood under the breaches
execute as @e[type=marker,tag=sm_debris_spot,distance=..48] at @s run function sunman:world/decay/debris_drop
# and dead grass where the green was: 40 tufts
scoreboard players set #sm sm.i 0
scoreboard players set #sm sm.n 40
function sunman:world/decay/grass_loop
