# as & at a cycle being replaced by a new summon of its owner (tagged mc.self)
scoreboard players operation @a[tag=mc.self,limit=1] mc.stored = @s mc.fuel
function mastercycle:cycle/dismiss
