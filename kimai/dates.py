# -*- coding: utf-8 -*-

import parsedatetime

import itertools
from datetime import datetime, timedelta
from typing import List

from .models import Record


def parse(expression, relative_date=None):
    cal = parsedatetime.Calendar()
    struct, status = cal.parse(expression, relative_date)
    return datetime(*struct[:6])  # I know, right?


def find_gaps(records: List[Record], threshold):
    grouped_by_day = itertools.groupby(
        reversed(records),
        lambda r: r.start.strftime('%A, %d %b %Y')
    )

    result = []

    for day, entries in grouped_by_day:
        entries = list(entries)
        for index, entry in enumerate(entries):
            try:
                next_entry = entries[index + 1]
            except IndexError:
                break

            gap = next_entry.start - entry.end

            # If the time between entries is more than the threshold
            # we remember them for later.
            if gap > threshold:
                result.append(TimesheetGap(day, entry, next_entry, gap))

    return result


class TimesheetGap(object):
    def __init__(self, day, entry, next_entry, gap):
        self.day = day
        self.entry = entry
        self.next_entry = next_entry
        self.gap = gap
