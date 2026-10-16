# as & at a player right-clicking the cycle (mc.this) with a fuel item
scoreboard players operation #f mc.tmp = @e[type=armor_stand,tag=mc.this,limit=1] mc.fuel
execute if score #f mc.tmp >= #cfg.max_fuel mc.const run return run title @s actionbar {text:"The Master Cycle's tank is already full.",color:"aqua"}
scoreboard players operation #before mc.tmp = #f mc.tmp

# fuel value in ticks of throttle (20 = 1 second); the first matching item wins
scoreboard players set #add mc.tmp 0
execute if predicate mastercycle:fuel/redstone run function mastercycle:fuel/consume {item:"minecraft:redstone",amount:300}
execute if score #add mc.tmp matches 0 if predicate mastercycle:fuel/coal run function mastercycle:fuel/consume {item:"minecraft:coal",amount:600}
execute if score #add mc.tmp matches 0 if predicate mastercycle:fuel/charcoal run function mastercycle:fuel/consume {item:"minecraft:charcoal",amount:600}
execute if score #add mc.tmp matches 0 if predicate mastercycle:fuel/blaze_powder run function mastercycle:fuel/consume {item:"minecraft:blaze_powder",amount:1200}
execute if score #add mc.tmp matches 0 if predicate mastercycle:fuel/blaze_rod run function mastercycle:fuel/consume {item:"minecraft:blaze_rod",amount:2400}
execute if score #add mc.tmp matches 0 if predicate mastercycle:fuel/redstone_block run function mastercycle:fuel/consume {item:"minecraft:redstone_block",amount:2700}
execute if score #add mc.tmp matches 0 if predicate mastercycle:fuel/coal_block run function mastercycle:fuel/consume {item:"minecraft:coal_block",amount:5400}
execute if score #add mc.tmp matches 0 if predicate mastercycle:fuel/nether_star run function mastercycle:fuel/consume {item:"minecraft:nether_star",amount:1000000}
execute if score #add mc.tmp matches 0 run return fail

scoreboard players operation #f mc.tmp += #add mc.tmp
execute if score #f mc.tmp > #cfg.max_fuel mc.const run scoreboard players operation #f mc.tmp = #cfg.max_fuel mc.const
scoreboard players operation @e[type=armor_stand,tag=mc.this,limit=1] mc.fuel = #f mc.tmp
execute at @e[type=armor_stand,tag=mc.this,limit=1] run function mastercycle:fx/refuel

# feedback: seconds gained and the new tank level
scoreboard players operation #sec mc.tmp = #f mc.tmp
scoreboard players operation #sec mc.tmp -= #before mc.tmp
scoreboard players operation #sec mc.tmp /= #20 mc.const
scoreboard players operation #pct mc.tmp = #f mc.tmp
scoreboard players operation #pct mc.tmp *= #100 mc.const
scoreboard players operation #pct mc.tmp /= #cfg.max_fuel mc.const
title @s actionbar [{text:"+",color:"aqua"},{score:{name:"#sec",objective:"mc.tmp"},color:"aqua"},{text:"s of fuel   ",color:"aqua"},{text:"tank ",color:"gray"},{score:{name:"#pct",objective:"mc.tmp"},color:"white"},{text:"%",color:"gray"}]
