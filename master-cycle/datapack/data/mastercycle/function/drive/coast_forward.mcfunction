scoreboard players operation @s mc.speed -= #dec mc.tmp
execute if score @s mc.speed matches ..-1 run scoreboard players set @s mc.speed 0
