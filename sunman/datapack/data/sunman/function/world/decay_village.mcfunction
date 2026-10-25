# THE ABANDONED VILLAGE, where you stand.
# DESTRUCTIVE AND PERMANENT: torches out, glass and beds and banners gone, stone aged,
# fields dead, walls torn open, the villagers replaced by their bodies. There is no undo.
# Refuses within 40 blocks of a place that has already been decayed.
execute align xyz if entity @e[type=marker,tag=sunman_decayed,distance=..40] run return run tellraw @s {text:"This place is already dead.",color:"dark_red"}
execute align xyz run function sunman:world/decay/guarded
execute align xyz if entity @e[type=marker,tag=sunman_decayed,distance=..1] run tellraw @s {text:"Once a peaceful home... now a place of silence, ruin, and blood.",color:"dark_red",italic:true}
