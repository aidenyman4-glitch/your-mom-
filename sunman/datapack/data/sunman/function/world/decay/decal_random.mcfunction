# At the ground. Trample what grows there, then one of three decals at a random yaw.
execute if block ~ ~ ~ #sunman:plants run setblock ~ ~ ~ air
execute store result storage sunman:village d.yaw int 1 run random value -180..180
execute store result score #sm sm.rng run random value 0..9
data modify storage sunman:village d.model set value "sunman:blood_splatter"
execute if score #sm sm.rng matches 0..3 run data modify storage sunman:village d.model set value "sunman:blood_pool"
execute if score #sm sm.rng matches 8..9 run data modify storage sunman:village d.model set value "sunman:blood_trail"
function sunman:world/decay/decal with storage sunman:village d
