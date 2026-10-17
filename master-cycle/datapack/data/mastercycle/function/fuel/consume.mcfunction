# as a player. Macro args: item = fuel item id, amount = fuel ticks it is worth
$scoreboard players set #add mc.tmp $(amount)
$execute unless entity @s[gamemode=creative] run clear @s $(item) 1
