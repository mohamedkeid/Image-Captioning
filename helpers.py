import math
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import os
import time


def show_plot(points):
    plt.figure()
    fig, ax = plt.subplots()
    loc = ticker.MultipleLocator(base=0.2) # put ticks at regular intervals
    ax.yaxis.set_major_locator(loc)
    plt.plot(points)


def as_minutes(s):
    m = math.floor(s / 60)
    s -= m * 60
    return '%dm %ds' % (m, s)


def time_since(since, percent):
    now = time.time()
    s = now - since
    es = s / (percent)
    rs = es - s
    return '%s (- %s)' % (as_minutes(s), as_minutes(rs))


def validate_path(p):
    p = os.path.abspath(p)
    if not os.path.exists(p):
        print("Path '{}' does not exist. Please provide a valid image path to annotate.".format(p))
        exit(1)
