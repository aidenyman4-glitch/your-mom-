# as a cycle: remove it and its click hitbox (riders are dismounted)
scoreboard players operation #cid mc.tmp = @s mc.cid
execute as @e[type=interaction,tag=mc.hitbox] if score @s mc.cid = #cid mc.tmp run kill @s
data remove entity @s equipment
kill @s
