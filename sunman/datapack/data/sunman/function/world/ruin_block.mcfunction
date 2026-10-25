# One probe. Wood goes; webs hang where a ceiling is left; dead bushes on bare ground.
execute if block ~ ~ ~ #sunman:ruinable run setblock ~ ~ ~ air
execute if block ~ ~ ~ #minecraft:air if block ~ ~1 ~ #minecraft:planks run setblock ~ ~ ~ cobweb
execute if block ~ ~ ~ #minecraft:air if block ~ ~-1 ~ coarse_dirt run setblock ~ ~ ~ dead_bush
