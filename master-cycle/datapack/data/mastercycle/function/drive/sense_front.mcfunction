# as & at a cycle moving forward (local coords follow its heading).
# The tyre's front edge is ~1.4 blocks ahead of the cycle's centre. Probes look
# that far plus up to one tick of travel, so the nose never enters a wall.
# Body height = 1 block above the ground the wheels stand on.
execute if block ^ ^1.2 ^1.45 #minecraft:blocks_motion run return run function mastercycle:drive/wall
execute if block ^0.3 ^1.1 ^1.15 #minecraft:blocks_motion run return run function mastercycle:drive/wall
execute if block ^-0.3 ^1.1 ^1.15 #minecraft:blocks_motion run return run function mastercycle:drive/wall
# further probes switch on as soon as one tick of travel could carry the
# nose past the previous one (0.15 apart, so no gap can be skipped)
execute if score @s mc.speed matches 80.. if block ^ ^1.2 ^1.60 #minecraft:blocks_motion run return run function mastercycle:drive/wall
execute if score @s mc.speed matches 230.. if block ^ ^1.2 ^1.75 #minecraft:blocks_motion run return run function mastercycle:drive/wall
execute if score @s mc.speed matches 380.. if block ^ ^1.2 ^1.90 #minecraft:blocks_motion run return run function mastercycle:drive/wall
execute if score @s mc.speed matches 530.. if block ^ ^1.2 ^2.05 #minecraft:blocks_motion run return run function mastercycle:drive/wall
execute if score @s mc.speed matches 680.. if block ^ ^1.2 ^2.20 #minecraft:blocks_motion run return run function mastercycle:drive/wall
execute if score @s mc.speed matches 830.. if block ^ ^1.2 ^2.35 #minecraft:blocks_motion run return run function mastercycle:drive/wall
# a knee-high block ahead with room above it: hop the front wheel up onto it
# now, instead of the nose clipping into it until the centre reaches the step
execute if block ^ ^0.3 ^1.45 #minecraft:blocks_motion unless block ^ ^1.3 ^1.45 #minecraft:blocks_motion if predicate mastercycle:on_ground run function mastercycle:drive/step_up
execute if score @s mc.speed matches 250.. if block ^ ^0.3 ^1.75 #minecraft:blocks_motion unless block ^ ^1.3 ^1.75 #minecraft:blocks_motion if predicate mastercycle:on_ground run function mastercycle:drive/step_up
