# as the online owner of the cycle being synced
# the owner summoned a newer cycle since this one was saved: this one is stale
execute unless score @s mc.gen = #g mc.tmp run return run scoreboard players set #stale mc.tmp 1
scoreboard players operation @s mc.stored = #f mc.tmp
