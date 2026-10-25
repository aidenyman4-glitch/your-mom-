# Full height where the ceiling allows; bowed under it where it does not.
execute if score #sm sm.head matches 4.. run function sunman:spawn/locust
execute if score #sm sm.head matches ..3 run function sunman:spawn/locust_cramped
scoreboard players set #sm sm.ok 1
return 1
