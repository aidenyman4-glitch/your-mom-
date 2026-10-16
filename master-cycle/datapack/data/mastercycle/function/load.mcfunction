# Master Cycle — runs on /reload and world load (via #minecraft:load)

# ---- per-entity state ------------------------------------------------------
scoreboard objectives add mc.fuel dummy
scoreboard objectives add mc.speed dummy
scoreboard objectives add mc.yaw dummy
scoreboard objectives add mc.cid dummy
scoreboard objectives add mc.owner dummy
scoreboard objectives add mc.gen dummy
scoreboard objectives add mc.hum dummy
scoreboard objectives add mc.jcd dummy
scoreboard objectives add mc.boost dummy
scoreboard objectives add mc.ridden dummy
scoreboard objectives add mc.air dummy
scoreboard objectives add mc.low dummy
scoreboard objectives add mc.skid dummy
# ---- per-player state ------------------------------------------------------
scoreboard objectives add mc.id dummy
scoreboard objectives add mc.stored dummy
scoreboard objectives add mc.cd dummy
scoreboard objectives add mc.use minecraft.used:minecraft.warped_fungus_on_a_stick
# ---- scratch & constants ---------------------------------------------------
scoreboard objectives add mc.tmp dummy
scoreboard objectives add mc.const dummy

scoreboard players set #-1 mc.const -1
scoreboard players set #4 mc.const 4
scoreboard players set #5 mc.const 5
scoreboard players set #10 mc.const 10
scoreboard players set #20 mc.const 20
scoreboard players set #40 mc.const 40
scoreboard players set #72 mc.const 72
scoreboard players set #85 mc.const 85
scoreboard players set #100 mc.const 100
scoreboard players set #1000 mc.const 1000
scoreboard players set #4000 mc.const 4000

# ---- tuning: edit these, then /reload --------------------------------------
# Speeds are in thousandths of a block per tick (600 = 0.6 blocks/tick = 12 blocks/s).
scoreboard players set #cfg.max_speed mc.const 600
scoreboard players set #cfg.boost_speed mc.const 950
scoreboard players set #cfg.reverse_speed mc.const 150
scoreboard players set #cfg.accel mc.const 22
scoreboard players set #cfg.boost_accel mc.const 40
scoreboard players set #cfg.brake mc.const 45
scoreboard players set #cfg.coast mc.const 10
scoreboard players set #cfg.coast_empty mc.const 30
# Steering, in hundredths of a degree per tick.
scoreboard players set #cfg.turn mc.const 450
scoreboard players set #cfg.turn_slow mc.const 250
scoreboard players set #cfg.turn_boost mc.const 320
# Fuel: one unit burns per tick of throttle, so 20 units = 1 second of riding.
scoreboard players set #cfg.max_fuel mc.const 6000
scoreboard players set #cfg.starter_fuel mc.const 1200
scoreboard players set #cfg.boost_burn mc.const 3
scoreboard players set #cfg.jump_burn mc.const 25

# Low-fuel warning chime when the tank drops to this (default 20%).
scoreboard players set #cfg.low_fuel mc.const 1200

scoreboard players operation #cfg.reverse_neg mc.const = #cfg.reverse_speed mc.const
scoreboard players operation #cfg.reverse_neg mc.const *= #-1 mc.const

scoreboard players add #next_id mc.id 0
scoreboard players add #next_cid mc.cid 0
scoreboard players add #tick mc.tmp 0
data modify storage mastercycle:tmp m set value [0.0d, 0.0d, 0.0d]
data modify storage mastercycle:hud bar set value ""
