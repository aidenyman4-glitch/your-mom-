# as & at a player right-clicking with a Master Cycle item: put the bike down
execute if score @s mc.cd matches 1.. run return fail
execute if predicate mastercycle:is_passenger run return run title @s actionbar {text:"Get off what you're riding to place your Master Cycle.",color:"gray"}
scoreboard players set @s mc.cd 20
function mastercycle:cycle/summon
execute unless entity @s[gamemode=creative] run clear @s minecraft:warped_fungus_on_a_stick[minecraft:custom_data~{mastercycle_bike:1b}] 1
