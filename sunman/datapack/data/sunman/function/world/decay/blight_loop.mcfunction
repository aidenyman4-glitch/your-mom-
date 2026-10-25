function sunman:world/decay/blight_probe
scoreboard players add #sm sm.i 1
execute if score #sm sm.i < #sm sm.n run function sunman:world/decay/blight_loop
