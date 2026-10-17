# as a player without an id: give them a unique number (used to own a cycle)
scoreboard players add #next_id mc.id 1
scoreboard players operation @s mc.id = #next_id mc.id
