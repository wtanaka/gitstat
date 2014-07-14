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
import sys

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

def make_timeseries(grouped_lines, window_size):
    """Convert the output of group_by_author into timeseries data
    suitable for flot
    """
    timeseries = {}
    for email, commits in grouped_lines:
        timeseries[email] = []
        # List of commits 
        commitwindow = []
        for commit in commits:
            timetuple = commit[TIME].utctimetuple()
            commitwindow.append(commit)
            commitwindow = removecommitsbefore(commitwindow,
                  commit[TIME] - window_size)
            linestouched = sum(tuple(c[ADDS] + c[DELETES] for c in
                     commitwindow))
            pair = (1000 * calendar.timegm(timetuple), linestouched)
            timeseries[email].append(pair)
    return timeseries

def main():
    """Main function"""
    logging.basicConfig()
    parsed_lines = processed_lines(fileinput.input())
    sorted_lines = sort_by_author_date(parsed_lines)
    del parsed_lines
    grouped_lines = group_by_author(sorted_lines)
    del sorted_lines

    window_size = datetime.timedelta(days=30)

    timeseries = make_timeseries(grouped_lines, window_size)

    plotdata = [{
       'data': series,
       'label': label,
       'points': {'show': True},
       'lines': {'show': True, 'fill': True},
       'color': idx,
    } for idx, (label, series) in enumerate(timeseries.iteritems())]

    variables = {}
    variables['plotdata'] = json.dumps(plotdata)
    sys.stdout.write(render_template(variables))

if __name__ == "__main__":
    main()
