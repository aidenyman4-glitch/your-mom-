# as & at a player the first time they're seen with the pack installed:
# hand them the bike as an item (and a Sheikah Slate to recall it from afar)
tag @s add mc.welcomed
function mastercycle:give_bike
function mastercycle:give_slate
tellraw @s [{text:"◈ Master Cycle installed! ",color:"aqua",bold:true},{text:"Hold the Master Cycle item and right-click to place it, then right-click the bike to ride. Sneak + punch picks it back up. The Sheikah Slate calls it to you from anywhere.",color:"gray",bold:false}]
tellraw @s [{text:"  Mouse ",color:"white"},{text:"steer   ",color:"gray"},{text:"W/S ",color:"white"},{text:"throttle / brake   ",color:"gray"},{text:"A/D ",color:"white"},{text:"carve   ",color:"gray"},{text:"Ctrl ",color:"white"},{text:"boost   ",color:"gray"},{text:"Space ",color:"white"},{text:"hop   ",color:"gray"},{text:"Shift ",color:"white"},{text:"get off",color:"gray"}]
playsound minecraft:block.beacon.power_select master @s ~ ~ ~ 0.6 1.6
