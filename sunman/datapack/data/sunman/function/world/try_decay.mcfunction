# As and at a player near villagers. Finds a villager that remembers its village's
# meeting point (the bell) and decays the village there. Villagers with no bell -- a
# breeding pen, a trading hall -- never trigger it.
execute as @e[type=villager,distance=..56,sort=nearest] if data entity @s Brain.memories."minecraft:meeting_point".value.pos run return run function sunman:world/decay/from_villager
