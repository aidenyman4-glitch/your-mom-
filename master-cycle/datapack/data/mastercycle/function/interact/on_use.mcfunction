# as & at a hitbox that was right-clicked
function mastercycle:interact/tag_cycle
execute on target at @s run function mastercycle:interact/use
tag @e[type=armor_stand,tag=mc.this] remove mc.this
data remove entity @s interaction
