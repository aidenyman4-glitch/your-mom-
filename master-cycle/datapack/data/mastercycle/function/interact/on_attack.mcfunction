# as & at a hitbox that was left-clicked
function mastercycle:interact/tag_cycle
execute on attacker at @s run function mastercycle:interact/attack
tag @e[type=armor_stand,tag=mc.this] remove mc.this
data remove entity @s attack
