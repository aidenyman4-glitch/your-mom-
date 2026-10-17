# as a player who just died: note it, and clear the dropped slate so it isn't
# duplicated when we hand one back on respawn
scoreboard players reset @s mc.death
scoreboard players set @s mc.lost 1
execute at @s as @e[type=item,distance=..16] if data entity @s Item.components."minecraft:custom_data".mastercycle_slate run kill @s
