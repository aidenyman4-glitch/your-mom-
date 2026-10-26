# A loose head or an arm, and the splash it made.
execute if block ~ ~ ~ #sunman:plants run setblock ~ ~ ~ air
$execute if score #sm sm.rng matches 0..49 run summon item_display ~ ~ ~ {Tags:["sunman_corpse"],item:{id:"minecraft:paper",count:1,components:{"minecraft:item_model":"sunman:dead_villager_head"}},item_display:"fixed",Rotation:[$(yaw)f,0f],view_range:1.2f,shadow_radius:0.35f}
$execute if score #sm sm.rng matches 50.. run summon item_display ~ ~ ~ {Tags:["sunman_corpse"],item:{id:"minecraft:paper",count:1,components:{"minecraft:item_model":"sunman:dead_villager_arm"}},item_display:"fixed",Rotation:[$(yaw)f,0f],view_range:1.2f,shadow_radius:0.3f}
$summon item_display ~ ~0.015 ~ {Tags:["sm_decal","sunman_blood"],item:{id:"minecraft:paper",count:1,components:{"minecraft:item_model":"sunman:blood_splatter"}},item_display:"fixed",Rotation:[$(yaw)f,0f],view_range:1.2f,shadow_radius:0f,brightness:{sky:4,block:0}}
function sunman:util/roll
scoreboard players set #sm sm.ok 1
