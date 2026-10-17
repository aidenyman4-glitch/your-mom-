# as & at a player the first time they're seen with the pack installed:
# hand them a Sheikah Slate so nobody needs commands or cheats to start riding
tag @s add mc.welcomed
function mastercycle:give_slate
tellraw @s [{text:"◈ Master Cycle installed! ",color:"aqua",bold:true},{text:"Hold the Sheikah Slate and right-click to summon your Master Cycle, then right-click the bike to ride. Sneak + punch puts it away.",color:"gray",bold:false}]
tellraw @s [{text:"  Mouse ",color:"white"},{text:"steer   ",color:"gray"},{text:"W/S ",color:"white"},{text:"throttle / brake   ",color:"gray"},{text:"A/D ",color:"white"},{text:"carve   ",color:"gray"},{text:"Ctrl ",color:"white"},{text:"boost   ",color:"gray"},{text:"Space ",color:"white"},{text:"jump   ",color:"gray"},{text:"Shift ",color:"white"},{text:"get off",color:"gray"}]
playsound minecraft:block.beacon.power_select master @s ~ ~ ~ 0.6 1.6
