execute if score @s sm.stage matches 2 run function sunman:world/decay/stage_ruin
execute if score @s sm.stage matches 3 run function sunman:world/decay/stage_rot
execute if score @s sm.stage matches 4 run function sunman:world/decay/stage_dead
execute if score @s sm.stage matches 5 run function sunman:world/decay/stage_blood
execute if score @s sm.stage matches 6 run function sunman:world/decay/stage_locusts
execute if score @s sm.stage matches 6 if entity @s[tag=sm_blackstone] run function sunman:world/decay/blackstone
scoreboard players add @s sm.stage 1
execute if score @s sm.stage matches 7.. run kill @s
execute if score @s sm.stage matches ..6 run schedule function sunman:world/decay/job 1t replace
