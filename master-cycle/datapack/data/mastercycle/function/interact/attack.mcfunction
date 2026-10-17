# as & at the player who punched a cycle (tagged mc.this)
execute unless entity @e[type=armor_stand,tag=mc.this] run return fail
execute if predicate mastercycle:is_passenger run return fail
execute unless predicate mastercycle:sneaking run return run title @s actionbar [{text:"Sneak + punch",color:"aqua"},{text:" to pick up the Master Cycle",color:"gray"}]
# only the owner (or someone in creative) may put it away
scoreboard players operation #o mc.tmp = @e[type=armor_stand,tag=mc.this,limit=1] mc.owner
execute unless score @s mc.id = #o mc.tmp unless entity @s[gamemode=creative] run return run title @s actionbar {text:"This Master Cycle belongs to someone else.",color:"red"}
execute if score @s mc.id = #o mc.tmp run scoreboard players operation @s mc.stored = @e[type=armor_stand,tag=mc.this,limit=1] mc.fuel
execute as @e[type=armor_stand,tag=mc.this] at @s run function mastercycle:cycle/dismiss
function mastercycle:bike/pick_up
title @s actionbar {text:"Master Cycle picked up - right-click the item to place it again.",color:"aqua"}
