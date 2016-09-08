#!/bin/bash
# THIS FILE IS PART OF THE CYLC SUITE ENGINE.
# Copyright (C) 2008-2016 NIWA
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
#-------------------------------------------------------------------------------
# Test that the state summary is updated when runahead tasks are released.
# GitHub #1981
. $(dirname $0)/test_header
#-------------------------------------------------------------------------------
set_test_number 3
#-------------------------------------------------------------------------------
install_suite $TEST_NAME_BASE release-update
#-------------------------------------------------------------------------------
TEST_NAME=$TEST_NAME_BASE-validate
run_ok $TEST_NAME cylc validate $SUITE_NAME
#-------------------------------------------------------------------------------
TEST_NAME=$TEST_NAME_BASE-check-states
cylc run $SUITE_NAME
sleep 10
cylc dump -t $SUITE_NAME | awk '{print $1 $3}' > log
cmp_ok log - << __END__
bar,succeeded,
bar,waiting,
foo,waiting,
__END__
#-------------------------------------------------------------------------------
TEST_NAME=$TEST_NAME_BASE-stop
run_ok $TEST_NAME cylc stop --max-polls=10 --interval=6 $SUITE_NAME
#-------------------------------------------------------------------------------
purge_suite $SUITE_NAME