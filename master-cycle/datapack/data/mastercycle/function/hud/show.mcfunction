# as the rider. Inputs: #hud_fuel, #hud_speed, #boosting (set by the cycle)
execute if score #hud_fuel mc.tmp matches ..0 run return run title @s actionbar [{text:"⚠ Fuel Empty! ",color:"red",bold:true},{text:"Right-click the cycle with coal, redstone, blaze powder or a nether star",color:"gray",bold:false}]

# fuel % (rounded up so the last drop still shows 1%) and speed in km/h (1 block = 1 m)
scoreboard players operation #pct mc.tmp = #hud_fuel mc.tmp
scoreboard players operation #pct mc.tmp *= #100 mc.const
scoreboard players operation #pct mc.tmp += #cfg.max_fuel mc.const
scoreboard players remove #pct mc.tmp 1
scoreboard players operation #pct mc.tmp /= #cfg.max_fuel mc.const
execute if score #pct mc.tmp matches 101.. run scoreboard players set #pct mc.tmp 100
scoreboard players operation #kmh mc.tmp = #hud_speed mc.tmp
execute if score #kmh mc.tmp matches ..-1 run scoreboard players operation #kmh mc.tmp *= #-1 mc.const
scoreboard players operation #kmh mc.tmp *= #72 mc.const
scoreboard players operation #kmh mc.tmp /= #1000 mc.const
function mastercycle:hud/bar

execute if score #boosting mc.tmp matches 1 run return run title @s actionbar [{text:"◈ ",color:"aqua"},{nbt:"bar",storage:"mastercycle:hud",color:"aqua"},{text:" ",color:"gray"},{score:{name:"#pct",objective:"mc.tmp"},color:"white"},{text:"%   ",color:"gray"},{score:{name:"#kmh",objective:"mc.tmp"},color:"white"},{text:" km/h  ",color:"gray"},{text:"BOOST",color:"gold",bold:true}]
execute if score #pct mc.tmp matches ..20 run return run title @s actionbar [{text:"◈ ",color:"red"},{nbt:"bar",storage:"mastercycle:hud",color:"gold"},{text:" ",color:"gray"},{score:{name:"#pct",objective:"mc.tmp"},color:"gold"},{text:"%  low fuel   ",color:"gray"},{score:{name:"#kmh",objective:"mc.tmp"},color:"white"},{text:" km/h",color:"gray"}]
title @s actionbar [{text:"◈ ",color:"aqua"},{nbt:"bar",storage:"mastercycle:hud",color:"aqua"},{text:" ",color:"gray"},{score:{name:"#pct",objective:"mc.tmp"},color:"white"},{text:"%   ",color:"gray"},{score:{name:"#kmh",objective:"mc.tmp"},color:"white"},{text:" km/h",color:"gray"}]
