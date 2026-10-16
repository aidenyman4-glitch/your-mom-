# Fill every loaded Master Cycle's tank.   Usage: /function mastercycle:admin/refuel_all
execute as @e[type=armor_stand,tag=mc.cycle] run scoreboard players operation @s mc.fuel = #cfg.max_fuel mc.const
