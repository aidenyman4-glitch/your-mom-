# 3.5: the ruin, 130 probes
scoreboard players set #sm sm.i 0
scoreboard players set #sm sm.n 130
function sunman:world/decay/ruin_loop
# something went through the walls: 40 places torn open, clawed through, caved in
scoreboard players set #sm sm.i 0
scoreboard players set #sm sm.try 320
function sunman:world/decay/smash_search
# two roofs fallen in
scoreboard players set #sm sm.i 0
scoreboard players set #sm sm.try 200
function sunman:world/decay/collapse_search
kill @e[type=marker,tag=sm_collapse]
