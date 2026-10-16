# as & at a cycle with a player on it
scoreboard players set #fwd mc.tmp 0
scoreboard players set #back mc.tmp 0
scoreboard players set #left mc.tmp 0
scoreboard players set #right mc.tmp 0
scoreboard players set #jump mc.tmp 0
scoreboard players set #sprint mc.tmp 0
execute on passengers if entity @s[type=player] run function mastercycle:drive/read_input

function mastercycle:drive/physics
function mastercycle:drive/fx

scoreboard players operation #hud_fuel mc.tmp = @s mc.fuel
scoreboard players operation #hud_speed mc.tmp = @s mc.speed
execute on passengers if entity @s[type=player] run function mastercycle:hud/show
