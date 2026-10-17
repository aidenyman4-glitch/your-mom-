# as & at a ridden cycle, after the rider's input has been read
#   W = throttle, S = brake / reverse, A/D = steer, Sprint (Ctrl) = boost, Space = hop
scoreboard players set #burn mc.tmp 0
scoreboard players set #skid mc.tmp 0
scoreboard players set #pow mc.tmp 0
execute if score @s mc.fuel matches 1.. run scoreboard players set #pow mc.tmp 1
scoreboard players set #boosting mc.tmp 0
execute if score #pow mc.tmp matches 1 if score #sprint mc.tmp matches 1 if score #fwd mc.tmp matches 1 unless score #back mc.tmp matches 1 run scoreboard players set #boosting mc.tmp 1

# ---- throttle: 0 = coast, 1 = accelerate, 2 = brake / reverse ---------------
scoreboard players set #mode mc.tmp 0
execute if score #pow mc.tmp matches 1 if score #fwd mc.tmp matches 1 unless score #back mc.tmp matches 1 run scoreboard players set #mode mc.tmp 1
execute if score #back mc.tmp matches 1 unless score #fwd mc.tmp matches 1 run scoreboard players set #mode mc.tmp 2
execute if score #mode mc.tmp matches 0 run function mastercycle:drive/coast
execute if score #mode mc.tmp matches 1 run function mastercycle:drive/accelerate
execute if score #mode mc.tmp matches 2 run function mastercycle:drive/brake

# ---- steering: the bike carves toward where the rider is looking ------------
# (the camera stays entirely under the mouse, so the view is perfectly smooth)
function mastercycle:drive/steer

# ---- hop --------------------------------------------------------------------
# Coyote time: for a few ticks after leaving the ground you can still jump.
# Jump buffer: pressing Space just before landing jumps on touchdown.
scoreboard players set #hop mc.tmp 0
execute if score @s mc.jcd matches 1.. run scoreboard players remove @s mc.jcd 1
execute if predicate mastercycle:on_ground run scoreboard players operation @s mc.coyote = #cfg.coyote mc.const
execute unless predicate mastercycle:on_ground if score @s mc.coyote matches 1.. run scoreboard players remove @s mc.coyote 1
execute if score #jump mc.tmp matches 1 run scoreboard players operation @s mc.jbuf = #cfg.jump_buffer mc.const
execute unless score #jump mc.tmp matches 1 if score @s mc.jbuf matches 1.. run scoreboard players remove @s mc.jbuf 1
execute if score @s mc.jbuf matches 1.. if score @s mc.coyote matches 1.. if score #pow mc.tmp matches 1 unless score @s mc.jcd matches 1.. run function mastercycle:drive/hop

# ---- fuel -------------------------------------------------------------------
scoreboard players operation @s mc.fuel -= #burn mc.tmp
execute if score #pow mc.tmp matches 1 if score @s mc.fuel matches ..0 run function mastercycle:drive/ran_out

# ---- push the armor stand ---------------------------------------------------
scoreboard players set #move mc.tmp 0
execute unless score @s mc.speed matches 0 run scoreboard players set #move mc.tmp 1
execute if score #hop mc.tmp matches 1 run scoreboard players set #move mc.tmp 1
execute if score #move mc.tmp matches 1 run function mastercycle:drive/apply_motion
