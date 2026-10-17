# as the victim, positioned at the cycle's nose. Macro arg: d = damage
scoreboard players add #hit mc.tmp 1
$damage @s $(d) minecraft:player_attack by @a[tag=mc.rider,limit=1]
# fling it the way the bike is going (knockback from a point behind the nose)
execute at @s run tp @s ~ ~ ~
execute as @e[tag=mc.rammer,limit=1] at @s rotated as @s positioned ^ ^0.6 ^-1.5 run damage @n[tag=!mc.rammer,tag=!mc.rider,tag=!mc.hitbox,distance=..4] 0 minecraft:player_attack by @a[tag=mc.rider,limit=1]
