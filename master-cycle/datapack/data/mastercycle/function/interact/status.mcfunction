# as a player sneak-right-clicking a cycle: show its fuel
scoreboard players operation #f mc.tmp = @e[type=armor_stand,tag=mc.this,limit=1] mc.fuel
scoreboard players operation #pct mc.tmp = #f mc.tmp
scoreboard players operation #pct mc.tmp *= #100 mc.const
scoreboard players operation #pct mc.tmp /= #cfg.max_fuel mc.const
scoreboard players operation #sec mc.tmp = #f mc.tmp
scoreboard players operation #sec mc.tmp /= #20 mc.const
title @s actionbar [{text:"◈ Master Cycle  ",color:"aqua"},{text:"fuel ",color:"gray"},{score:{name:"#pct",objective:"mc.tmp"},color:"white"},{text:"%  (",color:"gray"},{score:{name:"#sec",objective:"mc.tmp"},color:"white"},{text:"s of throttle left)",color:"gray"}]
