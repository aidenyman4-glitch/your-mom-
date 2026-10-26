execute store result storage sunman:village p.bx int 1 run random value -14..14
execute store result storage sunman:village p.bz int 1 run random value -14..14
execute store result score #sm sm.rng run random value 0..5
execute if score #sm sm.rng matches 0 run data modify storage sunman:village p.item set value "minecraft:egg"
execute if score #sm sm.rng matches 1 run data modify storage sunman:village p.item set value "minecraft:wheat"
execute if score #sm sm.rng matches 2 run data modify storage sunman:village p.item set value "minecraft:stick"
execute if score #sm sm.rng matches 3 run data modify storage sunman:village p.item set value "minecraft:bread"
execute if score #sm sm.rng matches 4 run data modify storage sunman:village p.item set value "minecraft:wooden_hoe"
execute if score #sm sm.rng matches 5 run data modify storage sunman:village p.item set value "minecraft:bone"
function sunman:world/decay/item_at with storage sunman:village p
