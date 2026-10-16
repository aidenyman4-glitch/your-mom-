# as & at a ridden cycle with fuel: engine hum pitched by speed
scoreboard players set @s mc.hum 10
scoreboard players operation #as mc.tmp = @s mc.speed
execute if score #as mc.tmp matches ..-1 run scoreboard players operation #as mc.tmp *= #-1 mc.const
execute if score #as mc.tmp matches ..99 run return run playsound mastercycle:engine.hum neutral @a ~ ~ ~ 0.5 0.7
execute if score #as mc.tmp matches 100..299 run return run playsound mastercycle:engine.hum neutral @a ~ ~ ~ 0.6 0.85
execute if score #as mc.tmp matches 300..499 run return run playsound mastercycle:engine.hum neutral @a ~ ~ ~ 0.7 1.0
execute if score #as mc.tmp matches 500..699 run return run playsound mastercycle:engine.hum neutral @a ~ ~ ~ 0.8 1.2
playsound mastercycle:engine.hum neutral @a ~ ~ ~ 0.9 1.45
