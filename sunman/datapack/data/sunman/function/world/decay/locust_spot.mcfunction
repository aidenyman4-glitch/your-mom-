# A floor, three blocks clear above it, not a doorway, a wall at its back.
execute unless block ~ ~ ~ #sunman:passable run return fail
execute unless block ~ ~1 ~ #sunman:passable run return fail
execute unless block ~ ~2 ~ #sunman:passable run return fail
execute if block ~ ~-1 ~ #sunman:passable run return fail
execute if block ~1 ~1 ~ #sunman:solid if block ~-1 ~1 ~ #sunman:solid run return fail
execute if block ~ ~1 ~1 #sunman:solid if block ~ ~1 ~-1 #sunman:solid run return fail
scoreboard players set #sm sm.head 3
execute if block ~ ~3 ~ #sunman:passable run scoreboard players set #sm sm.head 4
# wall to the north: face south (yaw 0), and so on round
execute if block ~ ~1 ~-1 #sunman:solid if block ~ ~1 ~1 #sunman:passable rotated 0 0 positioned ^ ^ ^-0.2 run return run function sunman:world/decay/locust_place
execute if block ~ ~1 ~1 #sunman:solid if block ~ ~1 ~-1 #sunman:passable rotated 180 0 positioned ^ ^ ^-0.2 run return run function sunman:world/decay/locust_place
execute if block ~-1 ~1 ~ #sunman:solid if block ~1 ~1 ~ #sunman:passable rotated -90 0 positioned ^ ^ ^-0.2 run return run function sunman:world/decay/locust_place
execute if block ~1 ~1 ~ #sunman:solid if block ~-1 ~1 ~ #sunman:passable rotated 90 0 positioned ^ ^ ^-0.2 run return run function sunman:world/decay/locust_place
return fail
