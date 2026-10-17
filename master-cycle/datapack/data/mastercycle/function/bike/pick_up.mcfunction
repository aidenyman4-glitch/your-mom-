# as a player who just put their cycle away: hand them the bike as an item
# (only one: if they already carry a Master Cycle item, don't add another)
execute store result score #has mc.tmp run clear @s minecraft:warped_fungus_on_a_stick[minecraft:custom_data~{mastercycle_bike:1b}] 0
execute if score #has mc.tmp matches 0 run function mastercycle:give_bike
