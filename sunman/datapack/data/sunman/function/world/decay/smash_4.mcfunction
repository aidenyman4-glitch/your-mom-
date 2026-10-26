# torn open low down, the way something big gets in: a doorway where there was a wall
fill ~-1 ~ ~ ~1 ~2 ~ air replace #sunman:smashable
fill ~ ~ ~-1 ~ ~2 ~1 air replace #sunman:smashable
function sunman:world/decay/debris
return 1
