# as & at a cycle that just burned its last unit of fuel
scoreboard players set @s mc.fuel 0
playsound mastercycle:fuel.empty neutral @a[distance=..48] ~ ~ ~ 1 1
particle minecraft:large_smoke ~ ~0.5 ~ 0.3 0.2 0.3 0.01 12
execute on passengers if entity @s[type=player] run title @s actionbar {text:"⚠ Fuel Empty!",color:"red",bold:true}
