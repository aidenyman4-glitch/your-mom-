# as & at a cycle rolling backwards: the rear tyre ends ~0.8 blocks behind centre
execute if block ^ ^1.2 ^-0.95 #minecraft:blocks_motion run return run function mastercycle:drive/wall
execute if block ^ ^0.3 ^-0.95 #minecraft:blocks_motion if block ^ ^1.3 ^-0.95 #minecraft:blocks_motion run return run function mastercycle:drive/wall
