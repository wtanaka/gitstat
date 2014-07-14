#!/usr/bin/env python
#
# Copyright 2014 Wesley Tanaka <http://wtanaka.com/>
#
# This file is part of gitstat.
#
# gitstat is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# gitstat is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with gitstat.  If not, see <http://www.gnu.org/licenses/>.
"""Process the output of gitlogstat to produce a graph, by author,
of touched lines of codes (additions + deletions)
"""
import calendar
import datetime
import fileinput
import itertools
import json
import logging
import os.path

ADDS = 'adds'
DELETES = 'deletions'
EMAIL = 'email'
TIME = 'datetime'

ZERO = datetime.timedelta(0)
class UTC(datetime.tzinfo):
    """UTC"""
    def utcoffset(self, _dtime):
        return ZERO

    def tzname(self, _dtime):
        return "UTC"

    def dst(self, _dtime):
        return ZERO

MY_UTC = UTC()

def datetime_to_flot(a_datetime):
    """Convert a python datetime to a flot/javascript unix
    timestamp
    """
    timetuple = a_datetime.utctimetuple()
    return 1000 * calendar.timegm(timetuple)

def render_template(variables):
    """Return a HTML string rendered with the given variables"""
    file_handle = open(os.path.join(os.path.dirname(__file__),
            'lineedits.html.template'))
    return file_handle.read() % variables

def key_email_date(dictionary):
    """Returns (EMAIL, TIME)"""
    return (dictionary[EMAIL], dictionary[TIME])

def key_email(dictionary):
    """Returns the EMAIL key"""
    return dictionary[EMAIL]

def processed_lines(lines):
    """Takes an iterator of lines produced by gitlogstat and generate
    a series of dicts, one per commit.
    """
    commit = None
    for line in lines:
        line = line.strip()
        if line.startswith("COMMIT"):
            if (commit is not None and
                    (commit[ADDS] + commit[DELETES] > 0)):
                yield commit
            email, name, timestamp = line[6:].split('|')
            timestamp = long(timestamp)

            commit = {
                EMAIL: email,
                'name': name,
                TIME: datetime.datetime.fromtimestamp(timestamp, MY_UTC),
                ADDS: 0,
                DELETES: 0,
            }
        elif line == '':
            pass
        else:
            try:
                adds, removes, filename = line.split('\t')
                if adds == '-' and removes == '-':
                    logging.debug("Binary file: %s", filename)
                else:
                    commit[ADDS] += int(adds)
                    commit[DELETES] += int(removes)
            except ValueError:
                logging.error("Could not parse '%s'", line)
                raise

def sort_by_author_date(parsed_lines):
    """Takes a iterator of dicts produced by processed_lines() and
    returns a dict
    """
    return sorted(parsed_lines, key=key_email_date)

def group_by_author(sorted_lines):
    """Group the lines by author
    """
    return itertools.groupby(sorted_lines, key=key_email)

def removecommitsbefore(commitwindow, cutoff):
    """
    commitwindow - list of commits sorted ascending by date
    cutoff - datetime.datetime
    """
    while len(commitwindow) > 0 and commitwindow[0][TIME] < cutoff:
        commitwindow = commitwindow[1:]
    return commitwindow

def generate_windows(commits, window_size):
    """Given an iterable of commit dicts which is sorted (ascending) by
    date and a window size (expressed as a timedelta), generate pairs
    (datetime, list of commit) associating datetimes with a list of
    commits that appeared in the range [datetime-window_size, datetime]
    """
    commitwindow = []
    for commit in commits:
        commitwindow.append(commit)
        commitwindow = removecommitsbefore(commitwindow,
                commit[TIME] - window_size)
        yield (commit[TIME], commitwindow)

def make_timeseries(grouped_lines, window_size, aggregate_function):
    """Convert the output of group_by_author into timeseries data
    suitable for flot.  First groups commits into running windows of
    window_size, then calls aggregate_function on each window to
    produce the Y-axis value.
    """
    timeseries = []
    for email, commits in grouped_lines:
        datapoints = []
        y_value_sum = 0.0
        # List of commits 
        for thetime, commitlist in generate_windows(commits, window_size):
            flot_time = datetime_to_flot(thetime)
            y_value = aggregate_function(commitlist)
            y_value_sum += y_value
            pair = (flot_time, y_value)
            datapoints.append(pair)
        timeseries.append((y_value_sum, email, datapoints))
    for _unused, email, datapoints in sorted(timeseries, reverse=True):
        yield (email, datapoints)

def input_grouped_lines():
    """Parses the output of gitlogstat from standard input into
    commits grouped by author"""
    parsed_lines = processed_lines(fileinput.input())
    sorted_lines = sort_by_author_date(parsed_lines)
    del parsed_lines
    grouped_lines = group_by_author(sorted_lines)
    return grouped_lines

def make_plot_data(timeseries):
    """Turn time series data from make_timeseries into something
    suitable for passing to flot
    """
    plotdata = [{
       'data': series,
       'label': label,
       'points': {'show': True},
       'lines': {'show': True, 'fill': True},
       'color': idx,
    } for idx, (label, series) in enumerate(timeseries)]
    return plotdata

def render_timeseries(timeseries):
    """Return HTML for the given timeseries
    """
    plotdata = make_plot_data(timeseries) 
    variables = {}
    variables['plotdata'] = json.dumps(plotdata)
    return render_template(variables)
