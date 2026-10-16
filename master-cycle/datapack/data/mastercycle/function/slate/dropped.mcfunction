# as & at the player who dropped a Sheikah Slate
scoreboard players set #found mc.tmp 1
# send the slate straight back to their inventory
execute as @e[type=item,tag=mc.dropped_slate,limit=1] run data modify entity @s PickupDelay set value 0s
tp @e[type=item,tag=mc.dropped_slate,limit=1] @s
function mastercycle:slate/activate
