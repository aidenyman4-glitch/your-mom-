# as a fast-moving cycle. When an entity runs into a wall the game zeroes the
# blocked axes of its Motion, so if last tick's push mostly vanished we hit something.
execute store result score #ox mc.tmp run data get storage mastercycle:tmp m[0] 1000
execute store result score #oz mc.tmp run data get storage mastercycle:tmp m[2] 1000
execute if score #ox mc.tmp matches ..-1 run scoreboard players operation #ox mc.tmp *= #-1 mc.const
execute if score #oz mc.tmp matches ..-1 run scoreboard players operation #oz mc.tmp *= #-1 mc.const
scoreboard players operation #ox mc.tmp += #oz mc.tmp
scoreboard players operation #ox mc.tmp *= #5 mc.const
scoreboard players operation #es mc.tmp = @s mc.speed
execute if score #es mc.tmp matches ..-1 run scoreboard players operation #es mc.tmp *= #-1 mc.const
# remaining motion < 20% of the speed we pushed with -> crash
execute if score #ox mc.tmp < #es mc.tmp run function mastercycle:drive/bump
