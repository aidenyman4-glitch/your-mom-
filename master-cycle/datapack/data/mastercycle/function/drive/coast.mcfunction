# as a cycle: no throttle (or no fuel) — roll to a stop. Out of fuel stops much faster.
scoreboard players operation #dec mc.tmp = #cfg.coast mc.const
execute if score #pow mc.tmp matches 0 run scoreboard players operation #dec mc.tmp = #cfg.coast_empty mc.const
execute if score @s mc.speed matches 1.. run function mastercycle:drive/coast_forward
execute if score @s mc.speed matches ..-1 run function mastercycle:drive/coast_backward
