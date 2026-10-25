execute store result storage sunman:village p.bx int 1 run random value -13..13
execute store result storage sunman:village p.bz int 1 run random value -13..13
execute store result storage sunman:village p.yaw int 1 run random value -180..180
# which body: a, b or c (the model ids are letters, so the roll is mapped, not stored)
execute store result score #sm sm.rng run random value 0..2
execute if score #sm sm.rng matches 0 run data modify storage sunman:village p.v set value "a"
execute if score #sm sm.rng matches 1 run data modify storage sunman:village p.v set value "b"
execute if score #sm sm.rng matches 2 run data modify storage sunman:village p.v set value "c"
execute store success score #sm sm.ok run function sunman:world/decay/corpse_at with storage sunman:village p
execute if score #sm sm.ok matches 1 run scoreboard players add #sm sm.i 1
scoreboard players remove #sm sm.try 1
execute if score #sm sm.i < #sm sm.n if score #sm sm.try matches 1.. run function sunman:world/decay/corpse_search
