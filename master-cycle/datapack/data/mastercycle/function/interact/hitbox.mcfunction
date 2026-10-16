# as & at each cycle hitbox (interaction entity): was it clicked?
execute if data entity @s interaction run function mastercycle:interact/on_use
execute if data entity @s attack run function mastercycle:interact/on_attack
