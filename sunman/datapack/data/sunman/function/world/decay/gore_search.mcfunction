execute store result storage sunman:village p.bx int 1 run random value -14..14
execute store result storage sunman:village p.bz int 1 run random value -14..14
execute store result storage sunman:village p.yaw int 1 run random value -180..180
execute store success score #sm sm.ok run function sunman:world/decay/gore_at with storage sunman:village p
execute if score #sm sm.ok matches 1 run scoreboard players add #sm sm.i 1
scoreboard players remove #sm sm.try 1
execute if score #sm sm.i < #sm sm.n if score #sm sm.try matches 1.. run function sunman:world/decay/gore_search
