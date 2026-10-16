# #r = 1000 * sin(#a degrees), for #a in [0, 360)
# Bhaskara I's approximation, max error ~0.0016:
#   sin(x) ~= 4x(180 - x) / (40500 - x(180 - x)),  0 <= x <= 180
scoreboard players operation #x mc.tmp = #a mc.tmp
scoreboard players set #sgn mc.tmp 1
execute if score #x mc.tmp matches 180.. run scoreboard players set #sgn mc.tmp -1
execute if score #x mc.tmp matches 180.. run scoreboard players remove #x mc.tmp 180
scoreboard players set #p mc.tmp 180
scoreboard players operation #p mc.tmp -= #x mc.tmp
scoreboard players operation #p mc.tmp *= #x mc.tmp
scoreboard players operation #r mc.tmp = #p mc.tmp
scoreboard players operation #r mc.tmp *= #4000 mc.const
scoreboard players set #d mc.tmp 40500
scoreboard players operation #d mc.tmp -= #p mc.tmp
scoreboard players operation #r mc.tmp /= #d mc.tmp
scoreboard players operation #r mc.tmp *= #sgn mc.tmp
