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
# tyre roll layered underneath: volume 0.2 -> 0.68, pitch 0.8 -> 1.28
scoreboard players operation #rv mc.tmp = #as mc.tmp
scoreboard players operation #rv mc.tmp *= #5 mc.const
scoreboard players operation #rv mc.tmp /= #10 mc.const
scoreboard players add #rv mc.tmp 2000
execute store result storage mastercycle:tmp hum.rv float 0.0001 run scoreboard players get #rv mc.tmp
scoreboard players operation #rp mc.tmp = #as mc.tmp
scoreboard players operation #rp mc.tmp *= #5 mc.const
scoreboard players operation #rp mc.tmp /= #10 mc.const
scoreboard players add #rp mc.tmp 8000
execute store result storage mastercycle:tmp hum.rp float 0.0001 run scoreboard players get #rp mc.tmp
function mastercycle:fx/hum_play with storage mastercycle:tmp hum
execute if predicate mastercycle:on_ground if score #as mc.tmp matches 60.. if score @s mc.wet matches 0 run function mastercycle:fx/roll_play with storage mastercycle:tmp hum
