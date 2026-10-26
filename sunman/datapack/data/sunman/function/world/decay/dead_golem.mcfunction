# As the spot marker: from a little above where it stood, down to the ground, and the
# golem lying on it. No blood.
tp @s ~ ~3 ~
scoreboard players set #sm sm.probe 0
execute at @s run function sunman:util/ground
execute store result storage sunman:village g.yaw int 1 run random value -180..180
execute at @s if block ~ ~ ~ #sunman:see_through unless block ~ ~-1 ~ #sunman:see_through run function sunman:world/decay/golem_body with storage sunman:village g
