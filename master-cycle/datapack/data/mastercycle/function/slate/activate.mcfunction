# as & at a player using their Sheikah Slate (right-click or drop)
execute if score @s mc.cd matches 1.. run return fail
scoreboard players set @s mc.cd 20
execute if predicate mastercycle:riding_cycle run return run title @s actionbar {text:"You're already riding a Master Cycle.",color:"gray"}
# the slate is a warped fungus on a stick, so it is also "used" to steer striders
execute if predicate mastercycle:is_passenger run return run title @s actionbar {text:"Get off what you're riding to summon your Master Cycle.",color:"gray"}
function mastercycle:cycle/summon
