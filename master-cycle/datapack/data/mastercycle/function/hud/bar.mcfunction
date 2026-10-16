# #pct (0-100) -> 10-segment fuel gauge in storage mastercycle:hud bar
scoreboard players operation #seg mc.tmp = #pct mc.tmp
scoreboard players add #seg mc.tmp 9
scoreboard players operation #seg mc.tmp /= #10 mc.const
execute if score #seg mc.tmp matches 0 run data modify storage mastercycle:hud bar set value "▯▯▯▯▯▯▯▯▯▯"
execute if score #seg mc.tmp matches 1 run data modify storage mastercycle:hud bar set value "▮▯▯▯▯▯▯▯▯▯"
execute if score #seg mc.tmp matches 2 run data modify storage mastercycle:hud bar set value "▮▮▯▯▯▯▯▯▯▯"
execute if score #seg mc.tmp matches 3 run data modify storage mastercycle:hud bar set value "▮▮▮▯▯▯▯▯▯▯"
execute if score #seg mc.tmp matches 4 run data modify storage mastercycle:hud bar set value "▮▮▮▮▯▯▯▯▯▯"
execute if score #seg mc.tmp matches 5 run data modify storage mastercycle:hud bar set value "▮▮▮▮▮▯▯▯▯▯"
execute if score #seg mc.tmp matches 6 run data modify storage mastercycle:hud bar set value "▮▮▮▮▮▮▯▯▯▯"
execute if score #seg mc.tmp matches 7 run data modify storage mastercycle:hud bar set value "▮▮▮▮▮▮▮▯▯▯"
execute if score #seg mc.tmp matches 8 run data modify storage mastercycle:hud bar set value "▮▮▮▮▮▮▮▮▯▯"
execute if score #seg mc.tmp matches 9 run data modify storage mastercycle:hud bar set value "▮▮▮▮▮▮▮▮▮▯"
execute if score #seg mc.tmp matches 10 run data modify storage mastercycle:hud bar set value "▮▮▮▮▮▮▮▮▮▮"
