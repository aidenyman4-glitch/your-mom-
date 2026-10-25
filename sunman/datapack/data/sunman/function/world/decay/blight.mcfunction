execute if block ~ ~ ~ #sunman:plants run setblock ~ ~ ~ air
fill ~-1 ~-1 ~-1 ~1 ~-1 ~1 coarse_dirt replace grass_block
fill ~ ~-1 ~-2 ~ ~-1 ~2 coarse_dirt replace grass_block
fill ~-2 ~-1 ~ ~2 ~-1 ~ coarse_dirt replace grass_block
function sunman:util/roll
execute if score #sm sm.rng matches ..54 if block ~ ~ ~ #minecraft:air run setblock ~ ~ ~ dead_bush
execute if score #sm sm.rng matches 30..74 if block ~1 ~ ~1 #minecraft:air if block ~1 ~-1 ~1 coarse_dirt run setblock ~1 ~ ~1 dead_bush
execute if score #sm sm.rng matches 60.. if block ~-1 ~ ~ #minecraft:air if block ~-1 ~-1 ~ coarse_dirt run setblock ~-1 ~ ~ short_dry_grass
