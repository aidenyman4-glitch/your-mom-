# as a player ~12 ticks after respawning (long enough for keepInventory to
# have restored the inventory, so a kept slate is actually seen)
scoreboard players set @s mc.lost 0
execute if items entity @s container.* minecraft:warped_fungus_on_a_stick[minecraft:custom_data~{mastercycle_slate:1b}] run return 0
execute if items entity @s weapon.offhand minecraft:warped_fungus_on_a_stick[minecraft:custom_data~{mastercycle_slate:1b}] run return 0
function mastercycle:give_slate
tellraw @s [{text:"◈ ",color:"aqua"},{text:"Your Sheikah Slate returns to you.",color:"gray"}]
playsound mastercycle:cycle.summon master @s ~ ~ ~ 0.5 1.3
