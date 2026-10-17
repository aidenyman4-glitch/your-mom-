# as & at a cycle moving forward fast: shove and hurt whatever the nose hits.
# damage = speed / #cfg.ram_div, capped at #cfg.ram_max; credited to the rider
# so drops and XP behave like a normal kill.
scoreboard players operation #dmg mc.tmp = @s mc.speed
scoreboard players operation #dmg mc.tmp /= #cfg.ram_div mc.const
execute if score #dmg mc.tmp > #cfg.ram_max mc.const run scoreboard players operation #dmg mc.tmp = #cfg.ram_max mc.const
execute store result storage mastercycle:tmp ram.d float 1 run scoreboard players get #dmg mc.tmp
scoreboard players set #hit mc.tmp 0
tag @s add mc.rammer
execute on passengers if entity @s[type=player] run tag @s add mc.rider
# nose box: everything within 1.6 blocks of a point just ahead of the front wheel
execute rotated as @s positioned ^ ^0.6 ^1.5 as @e[type=!#mastercycle:ram_immune,distance=..1.6,tag=!mc.rammer,tag=!mc.rider,tag=!mc.hitbox,limit=6,sort=nearest] run function mastercycle:drive/ram_hit with storage mastercycle:tmp ram
tag @e[tag=mc.rider] remove mc.rider
tag @s remove mc.rammer
execute if score #hit mc.tmp matches 1.. run function mastercycle:fx/ram
