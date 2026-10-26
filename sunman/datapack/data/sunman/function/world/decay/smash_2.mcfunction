# burst up through a roof
fill ~-1 ~ ~-1 ~1 ~1 ~1 air replace #sunman:smashable
fill ~ ~-1 ~ ~ ~2 ~ air replace #sunman:smashable
fill ~-2 ~1 ~ ~2 ~1 ~ air replace #sunman:roofing
function sunman:world/decay/debris
return 1
