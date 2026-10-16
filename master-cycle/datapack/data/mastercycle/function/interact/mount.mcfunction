# as & at a player climbing onto the cycle tagged mc.this
ride @s mount @e[type=armor_stand,tag=mc.this,limit=1]
execute unless predicate mastercycle:riding_cycle run return fail
# face the way the bike is pointing
execute rotated as @e[type=armor_stand,tag=mc.this,limit=1] run rotate @s ~ 10
scoreboard players set @e[type=armor_stand,tag=mc.this] mc.hum 20
scoreboard players set @e[type=armor_stand,tag=mc.this] mc.ridden 1
execute at @e[type=armor_stand,tag=mc.this,limit=1] run function mastercycle:fx/mount
execute if score @e[type=armor_stand,tag=mc.this,limit=1] mc.fuel matches ..0 run title @s actionbar [{text:"⚠ Fuel Empty! ",color:"red",bold:true},{text:"Right-click the cycle with coal, redstone, blaze powder or a nether star",color:"gray",bold:false}]
