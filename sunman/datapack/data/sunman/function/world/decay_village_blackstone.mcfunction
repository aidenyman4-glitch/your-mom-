# The Abandoned Village, then rebuilt in blackstone and coarse dirt: the biome sheet's
# older version, for worlds that want it. As destructive as the default, and more.
execute align xyz if entity @e[type=marker,tag=sunman_decayed,distance=..40] run return run tellraw @s {text:"This place is already dead.",color:"dark_red"}
execute align xyz run function sunman:world/decay/guarded
# the job's last stage rebuilds it in blackstone, after the ruin has had the wood
execute align xyz run tag @e[type=marker,tag=sm_decay_job,distance=..1] add sm_blackstone
