#!/bin/bash

# THIS FILE IS PART OF THE CYLC SUITE ENGINE.
# Copyright (C) 2008-2019 NIWA & British Crown (Met Office) & Contributors.
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

set -eu
set -o xtrace
shopt -s extglob

# Travis-CI install

args=("$@")

if grep -E '(unit-tests|functional-tests)' <<< "${args[@]}"; then
    brew install s-nail
fi

if grep 'unit-tests' <<< "${args[@]}"; then
    brew install shellcheck
fi

# TODO: remove when Travis env comes with a version of six >=1.12 (graphene)
pip3 install "six>=1.12"

pip3 install -e ."[all]"

# configure local SSH for Cylc jobs
ssh-keygen -t rsa -f ~/.ssh/id_rsa -N "" -q
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
ssh-keyscan -t rsa localhost >> ~/.ssh/known_hosts
