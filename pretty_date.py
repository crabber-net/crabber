from datetime import datetime, timedelta

# 11:15 AM · Apr 7, 2020

# 52m
# 3h
# Apr 7
# Dec 10, 2019

raw_ts = 1586311200
timestamp = datetime.utcfromtimestamp(1586311200)
now = datetime.utcnow()
delta = datetime.utcnow() - timestamp


def pretty():
    delta = datetime.utcnow() - timestamp

    if delta.seconds < 60:
        return f"{round(delta.seconds)}s"
    elif delta.seconds / 60 < 60:
        return f"{round(delta.seconds / 60)}m"
    elif delta.seconds / 60 / 60 < 24:
        return f"{round(delta.seconds / 60 / 60)}h"
    elif timestamp.year == now.year:
        return timestamp.strftime("%b %e")
    else:
        return timestamp.strftime("%b %e, %Y")


print(pretty())
