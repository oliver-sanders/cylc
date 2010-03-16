#!/bin/bash

# cylc example system, task startup
# one off initial task to clean the example system working directory
# no prerequisites

# run length 10 minutes

cylc message --started

# check environment
check-env.sh || exit 1

mkdir -p $TMPDIR || {
    MSG="failed to make $TMPDIR"
    echo "ERROR, startup: $MSG"
    cylc message -p CRITICAL $MSG
    cylc message --failed
    exit 1
}

sleep $(( 10 * 60 / REAL_TIME_ACCEL ))

echo "CLEANING $TMPDIR"
rm -rf $TMPDIR/* || {
    MSG="failed to clean $TMPDIR"
    echo "ERROR, startup: $MSG"
    cylc message -p CRITICAL $MSG
    cylc message --failed
    exit 1
}

cylc message --succeeded
