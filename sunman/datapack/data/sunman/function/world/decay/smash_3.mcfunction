# a roof caved in: the roofing gone over five by five, the frame left standing
execute if block ~ ~-3 ~ #sunman:see_through if block ~ ~-2 ~ #sunman:see_through run return fail
fill ~-2 ~-1 ~-2 ~2 ~1 ~2 air replace #sunman:roofing
fill ~-1 ~-2 ~-1 ~1 ~-2 ~1 air replace #minecraft:wooden_slabs
return 1
