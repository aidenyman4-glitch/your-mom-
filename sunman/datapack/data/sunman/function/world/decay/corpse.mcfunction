# A body, the blood it lies in, and for some the trail where it was dragged.
execute if block ~ ~ ~ #sunman:plants run setblock ~ ~ ~ air
$summon item_display ~ ~ ~ {Tags:["sunman_corpse"],item:{id:"minecraft:paper",count:1,components:{"minecraft:item_model":"sunman:dead_villager_$(v)"}},item_display:"fixed",Rotation:[$(yaw)f,0f],view_range:1.6f,shadow_radius:0.9f,shadow_strength:0.55f}
$summon item_display ~ ~0.015 ~ {Tags:["sm_decal","sunman_blood"],item:{id:"minecraft:paper",count:1,components:{"minecraft:item_model":"sunman:blood_pool"}},item_display:"fixed",Rotation:[$(yaw)f,0f],view_range:1.2f,shadow_radius:0f,brightness:{sky:4,block:0}}
# the drag mark runs back from the body along its length (the trail model is laid along z)
$execute if score #sm sm.rng matches ..49 rotated $(yaw) 0 positioned ^ ^ ^-1.6 if block ~ ~ ~ #sunman:see_through unless block ~ ~-1 ~ #sunman:see_through run summon item_display ~ ~0.016 ~ {Tags:["sm_decal","sunman_blood"],item:{id:"minecraft:paper",count:1,components:{"minecraft:item_model":"sunman:blood_trail"}},item_display:"fixed",Rotation:[$(yaw)f,0f],view_range:1.2f,shadow_radius:0f,brightness:{sky:4,block:0}}
function sunman:util/roll
scoreboard players set #sm sm.ok 1
