execute store result storage sunman:village p.bx int 1 run random value -15..15
execute store result storage sunman:village p.bz int 1 run random value -15..15
execute store result storage sunman:village p.yaw int 1 run random value -180..180
function sunman:util/roll
data modify storage sunman:village p.v set value "a"
execute if score #sm sm.rng matches 50.. run data modify storage sunman:village p.v set value "b"
function sunman:world/decay/grass_at with storage sunman:village p
