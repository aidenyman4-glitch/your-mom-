# As and at a player inside a dead village: now and then, whispering behind them.
function sunman:util/roll
execute if score #sm sm.rng matches ..3 rotated as @s positioned ^2 ^1 ^-6 run playsound sunman:village.whisper ambient @s ~ ~ ~ 0.7 1
execute if score #sm sm.rng matches 4 rotated as @s positioned ^-3 ^1 ^-8 run playsound sunman:village.whisper ambient @s ~ ~ ~ 0.5 0.85
