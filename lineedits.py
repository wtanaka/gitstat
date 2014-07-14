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
import datetime
import logging
import sys

import common

def main():
    """Main function"""
    logging.basicConfig()
    grouped_lines = common.input_grouped_lines()

    window_size = datetime.timedelta(days=30)

    timeseries = common.make_timeseries(grouped_lines, window_size,
        lambda commitlist: sum(tuple(c[common.ADDS] +
            c[common.DELETES] for c in commitlist)))

    sys.stdout.write(common.render_timeseries(timeseries))

if __name__ == "__main__":
    main()
