# as & at a player who right-clicked a warped fungus on a stick
scoreboard players reset @s mc.use
execute unless predicate mastercycle:holding_slate run return fail
function mastercycle:slate/activate
