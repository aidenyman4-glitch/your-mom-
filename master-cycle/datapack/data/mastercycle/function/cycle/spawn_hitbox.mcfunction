# as & at a cycle: create the interaction entity that catches right/left clicks
execute rotated as @s positioned ^ ^ ^0.5 run summon minecraft:interaction ~ ~ ~ {width:1.8f,height:1.3f,response:1b,Tags:["mc.hitbox","mc.synced","mc.newhb"]}
scoreboard players operation @e[type=interaction,tag=mc.newhb] mc.cid = @s mc.cid
tag @e[type=interaction,tag=mc.newhb] remove mc.newhb
scoreboard players set #found mc.tmp 1
