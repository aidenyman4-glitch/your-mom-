# as & at a ridden cycle with fuel: engine hum whose pitch and volume follow speed
#   pitch  0.65 at a standstill -> 1.46 at full boost
#   volume 0.45 at a standstill -> 0.83 at full boost
scoreboard players set @s mc.hum 10
scoreboard players operation #as mc.tmp = @s mc.speed
execute if score #as mc.tmp matches ..-1 run scoreboard players operation #as mc.tmp *= #-1 mc.const
# pitch x10000 = 6500 + speed * 8.5
scoreboard players operation #p mc.tmp = #as mc.tmp
scoreboard players operation #p mc.tmp *= #85 mc.const
scoreboard players operation #p mc.tmp /= #10 mc.const
scoreboard players add #p mc.tmp 6500
# volume x10000 = 4500 + speed * 4
scoreboard players operation #v mc.tmp = #as mc.tmp
scoreboard players operation #v mc.tmp *= #4 mc.const
scoreboard players add #v mc.tmp 4500
execute store result storage mastercycle:tmp hum.p float 0.0001 run scoreboard players get #p mc.tmp
execute store result storage mastercycle:tmp hum.v float 0.0001 run scoreboard players get #v mc.tmp
function mastercycle:fx/hum_play with storage mastercycle:tmp hum
