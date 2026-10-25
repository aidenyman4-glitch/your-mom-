# As an entity, at it: step it down until it stands in a see-through block over one
# that is not. At most 48 steps, counted in #sm sm.probe (reset it to 0 first).
# Returns 1 when it found ground, fails when it ran out.
scoreboard players add #sm sm.probe 1
execute if block ~ ~ ~ #sunman:see_through unless block ~ ~-1 ~ #sunman:see_through run return 1
execute if score #sm sm.probe matches 48.. run return fail
tp @s ~ ~-1 ~
execute at @s run return run function sunman:util/ground
