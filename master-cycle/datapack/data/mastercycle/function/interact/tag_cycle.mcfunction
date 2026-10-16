# as & at a hitbox: tag the cycle it belongs to with mc.this
scoreboard players operation #cid mc.tmp = @s mc.cid
execute as @e[type=armor_stand,tag=mc.cycle,distance=..6] if score @s mc.cid = #cid mc.tmp run tag @s add mc.this
