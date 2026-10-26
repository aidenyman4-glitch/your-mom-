# As a debris marker: down to the floor, and a piece of broken wood on it.
execute store result storage sunman:village w.yaw int 1 run random value -180..180
execute store result score #sm sm.rng run random value 0..2
execute if score #sm sm.rng matches 0 run data modify storage sunman:village w.v set value "a"
execute if score #sm sm.rng matches 1 run data modify storage sunman:village w.v set value "b"
execute if score #sm sm.rng matches 2 run data modify storage sunman:village w.v set value "c"
scoreboard players set #sm sm.probe 0
function sunman:util/ground
execute at @s if block ~ ~ ~ #minecraft:air unless block ~ ~-1 ~ #sunman:see_through unless entity @e[type=item_display,tag=sunman_debris,distance=..1.5] run function sunman:world/decay/wood_piece with storage sunman:village w
kill @s
