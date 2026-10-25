# 3.6: blood, 34 decals
scoreboard players set #sm sm.i 0
scoreboard players set #sm sm.n 34
function sunman:world/decay/blood_loop
# blood up the walls: 14 smears where something was dragged or raked
scoreboard players set #sm sm.i 0
scoreboard players set #sm sm.try 120
function sunman:world/decay/smear_search
# 3.8: what people left behind
scoreboard players set #sm sm.i 0
scoreboard players set #sm sm.n 10
function sunman:world/decay/items_loop
