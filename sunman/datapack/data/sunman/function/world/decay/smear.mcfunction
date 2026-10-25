# The smear model stands in its own z plane; yaw 0 puts it flat on a north wall.
summon item_display ~ ~ ~ {Tags:["sm_decal","sunman_blood","sm_new"],item:{id:"minecraft:paper",count:1,components:{"minecraft:item_model":"sunman:blood_smear"}},item_display:"fixed",view_range:1.0f,shadow_radius:0f,brightness:{sky:4,block:0}}
$execute as @e[type=item_display,tag=sm_new] run tp @s ~ ~ ~ $(yaw) 0
tag @e[type=item_display,tag=sm_new] remove sm_new
return 1
