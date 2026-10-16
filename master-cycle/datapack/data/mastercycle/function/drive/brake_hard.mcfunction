# as a cycle rolling forward with the brake held
execute if score @s mc.speed matches 300.. run scoreboard players set #skid mc.tmp 1
scoreboard players operation @s mc.speed -= #cfg.brake mc.const
execute if score @s mc.speed matches ..-1 run scoreboard players set @s mc.speed 0
