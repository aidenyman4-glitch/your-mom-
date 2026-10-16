# as & at a ridden cycle, after physics: exhaust particles + engine sounds

# boost kicked in this tick
execute if score #boosting mc.tmp matches 1 unless score @s mc.boost matches 1 run function mastercycle:fx/boost_start
scoreboard players operation @s mc.boost = #boosting mc.tmp

# Sheikah-blue exhaust behind the rear wheel while accelerating
execute if score #mode mc.tmp matches 1 rotated as @s run particle minecraft:end_rod ^ ^0.25 ^-0.85 0.06 0.04 0.06 0.005 1
execute if score #mode mc.tmp matches 1 if score #boosting mc.tmp matches 0 rotated as @s run particle minecraft:dust{color:[0.31f,0.89f,1.0f],scale:0.8f} ^ ^0.2 ^-0.9 0.12 0.05 0.12 0 2
# boosting: a much thicker cyan/blue plume
execute if score #boosting mc.tmp matches 1 rotated as @s run particle minecraft:soul_fire_flame ^ ^0.3 ^-0.95 0.1 0.06 0.1 0.02 3
execute if score #boosting mc.tmp matches 1 rotated as @s run particle minecraft:dust{color:[0.31f,0.89f,1.0f],scale:1.6f} ^ ^0.25 ^-1.0 0.15 0.08 0.15 0 4
execute if score #boosting mc.tmp matches 1 rotated as @s run particle minecraft:sculk_charge_pop ^ ^0.3 ^-1.0 0.1 0.05 0.1 0.01 2
execute if score #boosting mc.tmp matches 1 rotated as @s run particle minecraft:electric_spark ^ ^0.4 ^-0.7 0.2 0.1 0.2 0.3 2
# tyre smoke under hard braking
execute if score #skid mc.tmp matches 1 rotated as @s run particle minecraft:poof ^ ^0.1 ^-0.8 0.15 0.02 0.15 0.01 1

# engine hum, re-triggered every 10 ticks and pitched by speed
scoreboard players remove @s mc.hum 1
execute if score @s mc.hum matches ..0 if score @s mc.fuel matches 1.. run function mastercycle:fx/hum
