# as a cycle: S is held
# rolling forward: brake hard (works without fuel)
execute if score @s mc.speed matches 1.. run return run function mastercycle:drive/brake_hard
# stopped or rolling back: reverse slowly, which needs fuel
execute if score #pow mc.tmp matches 0 run return run function mastercycle:drive/coast
scoreboard players set #burn mc.tmp 1
scoreboard players remove @s mc.speed 12
execute if score @s mc.speed < #cfg.reverse_neg mc.const run scoreboard players operation @s mc.speed = #cfg.reverse_neg mc.const
