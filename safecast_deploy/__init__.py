import datetime
import sys
import time


def verbose_sleep(secs):
    end_time = (datetime.datetime.now() + datetime.timedelta(seconds=secs)).isoformat()
    print("Sleeping for " + str(secs) + " seconds until " + end_time, file=sys.stderr)
    time.sleep(secs)
