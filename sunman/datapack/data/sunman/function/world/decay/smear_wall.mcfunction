# Find which side the wall is on; hang the smear on its face, facing out into the room.
execute store result storage sunman:village s.yaw int 1 run random value -4..4
execute if block ~ ~ ~-1 #sunman:solid if block ~ ~1 ~-1 #sunman:solid align xyz positioned ~0.5 ~0.75 ~0.02 run return run function sunman:world/decay/smear with storage sunman:village s
execute if block ~ ~ ~1 #sunman:solid if block ~ ~1 ~1 #sunman:solid align xyz positioned ~0.5 ~0.75 ~0.98 rotated 180 0 run return run function sunman:world/decay/smear_r with storage sunman:village s
execute if block ~-1 ~ ~ #sunman:solid if block ~-1 ~1 ~ #sunman:solid align xyz positioned ~0.02 ~0.75 ~0.5 rotated -90 0 run return run function sunman:world/decay/smear_r with storage sunman:village s
execute if block ~1 ~ ~ #sunman:solid if block ~1 ~1 ~ #sunman:solid align xyz positioned ~0.98 ~0.75 ~0.5 rotated 90 0 run return run function sunman:world/decay/smear_r with storage sunman:village s
return fail
