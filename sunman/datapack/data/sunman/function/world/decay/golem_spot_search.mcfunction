# no golem here: lay one out in the open somewhere near the middle
execute store result storage sunman:village p.bx int 1 run random value -12..12
execute store result storage sunman:village p.bz int 1 run random value -12..12
execute store success score #sm sm.ok run function sunman:world/decay/golem_spot_at with storage sunman:village p
execute if score #sm sm.ok matches 1 run scoreboard players add #sm sm.i 1
scoreboard players remove #sm sm.try 1
execute if score #sm sm.i matches ..0 if score #sm sm.try matches 1.. run function sunman:world/decay/golem_spot_search
