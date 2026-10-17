# as & at an item entity on its first tick: is it a dropped Sheikah Slate?
tag @s add mc.seen
execute unless data entity @s Item.components."minecraft:custom_data".mastercycle_slate run return fail
tag @s add mc.dropped_slate
scoreboard players set #found mc.tmp 0
# the thrower summons the cycle; fall back to the nearest player if unknown
execute on origin if entity @s[type=player] at @s run function mastercycle:slate/dropped
execute if score #found mc.tmp matches 0 as @p[distance=..8,gamemode=!spectator] at @s run function mastercycle:slate/dropped
tag @s remove mc.dropped_slate
