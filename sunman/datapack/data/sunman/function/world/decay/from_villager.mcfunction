# As a villager: read where its bell is and decay the village round it.
data modify storage sunman:village c set value {}
data modify storage sunman:village c.x set from entity @s Brain.memories."minecraft:meeting_point".value.pos[0]
data modify storage sunman:village c.y set from entity @s Brain.memories."minecraft:meeting_point".value.pos[1]
data modify storage sunman:village c.z set from entity @s Brain.memories."minecraft:meeting_point".value.pos[2]
function sunman:world/decay/at_bell with storage sunman:village c
