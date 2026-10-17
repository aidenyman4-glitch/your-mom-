# as a player who has respawned after dying with Master Cycle gear
scoreboard players set @s mc.lost 0
execute store result score #has mc.tmp run clear @s minecraft:warped_fungus_on_a_stick[minecraft:custom_data~{mastercycle_slate:1b}] 0
execute if score #has mc.tmp matches 0 run function mastercycle:give_slate
# only replace the bike item if they have neither the item nor a placed cycle
execute store result score #has mc.tmp run clear @s minecraft:warped_fungus_on_a_stick[minecraft:custom_data~{mastercycle_bike:1b}] 0
scoreboard players operation #me mc.id = @s mc.id
scoreboard players set #placed mc.tmp 0
execute as @e[type=armor_stand,tag=mc.cycle] if score @s mc.owner = #me mc.id run scoreboard players set #placed mc.tmp 1
execute if score #has mc.tmp matches 0 if score #placed mc.tmp matches 0 run function mastercycle:give_bike
tellraw @s [{text:"◈ ",color:"aqua"},{text:"Your Sheikah Slate returns to you.",color:"gray"}]
playsound mastercycle:cycle.summon master @s ~ ~ ~ 0.5 1.3
