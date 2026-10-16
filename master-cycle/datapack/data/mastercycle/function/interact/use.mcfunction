# as & at the player who right-clicked a cycle (tagged mc.this)
execute unless entity @e[type=armor_stand,tag=mc.this] run return fail
# fuel in hand -> refuel (works while riding too)
execute if predicate mastercycle:holding_fuel run return run function mastercycle:fuel/add
# sneak + right-click -> fuel gauge
execute if predicate mastercycle:sneaking run return run function mastercycle:interact/status
execute if predicate mastercycle:is_passenger run return fail
execute if entity @e[type=armor_stand,tag=mc.this,predicate=mastercycle:has_rider] run return run title @s actionbar {text:"Someone is already riding this Master Cycle.",color:"gray"}
function mastercycle:interact/mount
