# Declares every objective the pack uses (OBJECTIVES in tools/export_datapack.py).
scoreboard objectives add sm.rng dummy
scoreboard objectives add sm.probe dummy
scoreboard objectives add sm.decay dummy
scoreboard objectives add sm.awake dummy
scoreboard objectives add sm.i dummy
scoreboard objectives add sm.n dummy
scoreboard objectives add sm.try dummy
scoreboard objectives add sm.ok dummy
scoreboard objectives add sm.decals dummy
scoreboard objectives add sm.head dummy
scoreboard objectives add sm.stage dummy
scoreboard objectives add sm.cy dummy
# villages decay when players come near, unless a world has switched it off
execute unless score #sm sm.decay matches -2147483648..2147483647 run scoreboard players set #sm sm.decay 1
data merge storage sunman:village {}
schedule function sunman:slow 20t replace
