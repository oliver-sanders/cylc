#!/usr/bin/env python3

# THIS FILE IS PART OF THE CYLC SUITE ENGINE.
# Copyright (C) NIWA & British Crown (Met Office) & Contributors.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""cylc install [OPTIONS] ARGS

Install a new suite.

Install the name REG for the suite definition in PATH. The suite server
program can then be started, stopped, and targeted by name REG. (Note that
"cylc run" can also install suites on the fly).

Installation creates a suite run directory "~/cylc-run/REG/" containing a
".service/source" symlink to the suite definition PATH. The .service directory
will also be used for server authentication files at run time.

Suite names can be hierarchical, corresponding to the path under ~/cylc-run.

Examples:
  # Register PATH/flow.cylc as dogs/fido
  # (with run directory ~/cylc-run/dogs/fido)
  $ cylc install dogs/fido PATH

  # Install $PWD/flow.cylc as dogs/fido.
  $ cylc install dogs/fido

  # Install $PWD/flow.cylc as the parent directory
  # name: $(basename $PWD).
  $ cylc install

The same suite can be installed with multiple names; this results in multiple
suite run directories that link to the same suite definition.

To "unregister" a suite, delete or rename its run directory (renaming it under
~/cylc-run effectively re-registers the original suite with the new name).

"""

from cylc.flow.option_parsers import CylcOptionParser as COP
from cylc.flow.install import install
from cylc.flow.terminal import cli_function


def get_option_parser():
    parser = COP(
        __doc__,
        argdoc=[("[REG]", "Workflow name"),
                ("[PATH]", "Workflow definition directory (defaults to $PWD)")])

    parser.add_option(
        "--redirect", help="Allow an existing suite name and run directory"
                           " to be used with another suite.",
        action="store_true", default=False, dest="redirect")

    parser.add_option(
        "--run-name", help="Name the run ",
        action="store", metavar="RUNDIR", default=None, dest="rundir")

    parser.add_option(
        "--run-dir", help="Symlink $HOME/cylc-run/REG to RUNDIR/REG.",
        action="store", metavar="RUNDIR", default=None, dest="rundir")




    return parser


@cli_function(get_option_parser)
def main(parser, opts, reg=None, src=None):
    install(reg, src, redirect=opts.redirect, rundir=opts.rundir)


if __name__ == "__main__":
    main()
