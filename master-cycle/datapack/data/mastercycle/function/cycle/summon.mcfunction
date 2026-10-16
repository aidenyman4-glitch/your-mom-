# as & at a player: summon their Master Cycle at their feet, facing where they look.
# Any cycle they already own is recalled (its fuel goes back into their slate).
tag @s add mc.self
scoreboard players operation #me mc.id = @s mc.id
execute as @e[type=armor_stand,tag=mc.cycle] if score @s mc.owner = #me mc.id at @s run function mastercycle:cycle/recall_old
tag @s remove mc.self

# brand new riders get a starter charge
execute unless score @s mc.stored matches 0.. run scoreboard players operation @s mc.stored = #cfg.starter_fuel mc.const
# bump the generation so a stale copy left in unloaded chunks removes itself
scoreboard players add @s mc.gen 1
scoreboard players operation #gen mc.tmp = @s mc.gen
scoreboard players operation #fuel mc.tmp = @s mc.stored

summon minecraft:armor_stand ~ ~ ~ {Tags:["mc.cycle","mc.new"],Invisible:1b,Invulnerable:1b,NoBasePlate:1b,Silent:1b,DisabledSlots:4144959,equipment:{head:{id:"minecraft:warped_fungus_on_a_stick",count:1,components:{"minecraft:custom_model_data":{floats:[7701f]}}}},attributes:[{id:"minecraft:scale",base:0.5d},{id:"minecraft:step_height",base:1.0d}]}
execute as @e[type=armor_stand,tag=mc.new] run function mastercycle:cycle/init
title @s actionbar [{text:"Master Cycle ready ",color:"aqua"},{text:"— right-click to ride",color:"gray"}]
