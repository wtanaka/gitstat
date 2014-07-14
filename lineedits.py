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
import json
import logging
import sys

import common

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
            timetuple = commit[common.TIME].utctimetuple()
            commitwindow.append(commit)
            commitwindow = common.removecommitsbefore(commitwindow,
                    commit[common.TIME] - window_size)
            linestouched = sum(tuple(c[common.ADDS] +
                    c[common.DELETES] for c in commitwindow))
            pair = (1000 * calendar.timegm(timetuple), linestouched)
            timeseries[email].append(pair)
    return timeseries

def main():
    """Main function"""
    logging.basicConfig()
    parsed_lines = common.processed_lines(fileinput.input())
    sorted_lines = common.sort_by_author_date(parsed_lines)
    del parsed_lines
    grouped_lines = common.group_by_author(sorted_lines)
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
    sys.stdout.write(common.render_template(variables))

if __name__ == "__main__":
    main()
