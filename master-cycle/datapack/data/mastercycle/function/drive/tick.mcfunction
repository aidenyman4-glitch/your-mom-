# as & at a cycle with a player on it
scoreboard players set #fwd mc.tmp 0
scoreboard players set #back mc.tmp 0
scoreboard players set #left mc.tmp 0
scoreboard players set #right mc.tmp 0
scoreboard players set #jump mc.tmp 0
scoreboard players set #sprint mc.tmp 0
execute on passengers if entity @s[type=player] run function mastercycle:drive/read_input

scoreboard players set @s mc.ridden 1
function mastercycle:drive/physics
# ram anything in front once we're moving with purpose
execute if score @s mc.speed matches 220.. run function mastercycle:drive/ram
function mastercycle:drive/fx

# landing after a hop or a drop (4+ ticks airborne)
execute unless predicate mastercycle:on_ground run scoreboard players add @s mc.air 1
execute if predicate mastercycle:on_ground if score @s mc.air matches 4.. run function mastercycle:fx/land
# the suspension soaks up the landing: no fall damage while riding
execute if predicate mastercycle:on_ground if score @s mc.air matches 4.. on passengers if entity @s[type=player] run function mastercycle:drive/soft_landing
execute if predicate mastercycle:on_ground run scoreboard players set @s mc.air 0

# one warning chime when the tank drops to the low-fuel line
execute if score @s mc.fuel matches 1.. if score @s mc.fuel <= #cfg.low_fuel mc.const unless score @s mc.low matches 1 run function mastercycle:fx/low_fuel
execute if score @s mc.fuel > #cfg.low_fuel mc.const run scoreboard players set @s mc.low 0

scoreboard players operation #hud_fuel mc.tmp = @s mc.fuel
scoreboard players operation #hud_speed mc.tmp = @s mc.speed
execute on passengers if entity @s[type=player] run function mastercycle:hud/show
