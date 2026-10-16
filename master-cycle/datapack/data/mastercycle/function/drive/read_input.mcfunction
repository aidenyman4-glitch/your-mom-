# as the rider: read their movement keys (player input predicate)
execute if predicate mastercycle:input/forward run scoreboard players set #fwd mc.tmp 1
execute if predicate mastercycle:input/backward run scoreboard players set #back mc.tmp 1
execute if predicate mastercycle:input/left run scoreboard players set #left mc.tmp 1
execute if predicate mastercycle:input/right run scoreboard players set #right mc.tmp 1
execute if predicate mastercycle:input/jump run scoreboard players set #jump mc.tmp 1
execute if predicate mastercycle:input/sprint run scoreboard players set #sprint mc.tmp 1
