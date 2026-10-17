# as & at a player who right-clicked a warped fungus on a stick
scoreboard players reset @s mc.use
execute if predicate mastercycle:holding_bike run return run function mastercycle:bike/place
execute unless predicate mastercycle:holding_slate run return fail
function mastercycle:slate/activate
