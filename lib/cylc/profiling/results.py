# THIS FILE IS PART OF THE CYLC SUITE ENGINE.
# Copyright (C) 2008-2017 NIWA
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

# NOTE: All fields are of type 'FLOAT' as they may be averaged values.
# WARNING: These fields are used to draw up the database schema.
RESULT_FIELDS = [
    'elapsed_time', 'cpu_time', 'user_time', 'system_time', 'rss_memory',
    'file_ins', 'file_outs', 'startup_time', 'main_loop_iterations',
    'average_main_loop_iteration_time', 'elapsed_non_sleep_time'
]  # TODO: New standadrised metric system...

import json
import os
import sqlite3
import sys
import tempfile
import unittest

import cylc.profiling as prof
import cylc.profiling.analysis as analysis
import cylc.profiling.git as git  # TODO: Rename utills?


def _results_sorter(one, two):
    # Platform.
    if one[0] < two[0]:
        return 1
    if one[0] > two[0]:
        return -1
    # Version.
    one_com = git.get_commit_date(one[1])
    two_com = git.get_commit_date(two[1])
    if one_com > two_com:
        return 1
    if one_com < two_com:
        return -1
    # Experiment.
    if one[2] > two[2]:
        return 1
    if one[2] < two[2]:
        return -1
    # Run.
    if one[3] > two[3]:
        return 1
    if one[3] < two[3]:
        return -1
    return 0


def _sync_experiments(conn, experiments=None, experiment_ids=None):
    if not experiment_ids:
        experiment_ids = [experiment['id'] for experiment in experiments]

    stmt = 'SELECT experiment_id FROM results WHERE experiment_id IN (%s)' % (
        ', '.join(['?'] * len(experiment_ids)))
    curr = conn.cursor()
    curr.execute(stmt, experiment_ids)
    exps_in_results = set(x[0] for x in curr.fetchall())

    stmt = ('SELECT experiment_id FROM experiments WHERE experiment_id IN '
            '(%s)' % (', '.join(['?'] * len(experiment_ids))))
    curr = conn.cursor()
    curr.execute(stmt, experiment_ids)
    exps_in_experiments = set(x[0] for x in curr.fetchall())

    if experiments:
        for experiment_id in exps_in_results - exps_in_experiments:
            # Experiment present in the results table but not in the experiments
            # table. Add an entry for it.
            stmt = 'INSERT INTO experiments VALUES(%s)' % (', '.join(['?'] * 3))
            experiment = filter_experiment(experiments, experiment_id)
            options = get_experiment_options(experiment)
            args = (experiment_id, experiment['name'], json.dumps(options))
            with conn:
                conn.execute(stmt, args)

    for experiment_id in exps_in_experiments - exps_in_results:
        # Experiment present in the experiments table but not used in the
        # results tabke. Remove this (unused) entry.
        stmt = 'DELETE FROM experiments WHERE experiment_id = (?)'
        with conn:
            conn.execute(stmt, experiment_id)


def _results_call(conn, platforms=None, version_ids=None, experiment_ids=None,
                  run_names=None, operator='SELECT'):
    where = []
    args = []
    if platforms:
        if not isinstance(platforms, list):
            platforms = [platforms]
        where.append('platform IN (%s)' % (', '.join(['?'] * len(platforms))))
        args.extend(platforms)
    if version_ids:
        if not isinstance(version_ids, list):
            version_ids = [version_ids]
        where.append(
            'version_id IN (%s)' % (', '.join(['?'] * len(version_ids))))
        args.extend(version_ids)
    if experiment_ids:
        if not isinstance(experiment_ids, list):
            experiment_ids = [experiment_ids]
        where.append(
            'experiment_id IN (%s)' % (', '.join(['?'] * len(experiment_ids))))
        args.extend(experiment_ids)
    if run_names:
        if not isinstance(run_names, list):
            run_names = [run_names]
        where.append(
            'run_name IN (%s)' % (', '.join(['?'] * len(run_names))))
        args.extend(run_names)

    if operator == 'SELECT':
        stmt = 'SELECT * from results'
    elif operator == 'DELETE':
        stmt = 'DELETE from results'
    else:
        raise Exception('Unsupported results operator "%s"' % operator)
    if where:
        stmt += ' WHERE %s' % ' AND '.join(where)

    if operator == 'SELECT':
        curr = conn.cursor()
        curr.execute(stmt, args)
        return curr.fetchall()
    else:
        with conn:
            conn.cursor().execute(stmt, args)


def get(*args, **kwargs):
    sort = False
    if 'sort' in kwargs:
        sort = kwargs['sort']
        del kwargs['sort']
    results = _results_call(*args, **kwargs)
    if sort:
        results.sort(_results_sorter)
    return results


def get_dict(*args, **kwargs):
    ret = []
    for result in get(*args, **kwargs):
        ret.append((result[0:4], dict((RESULT_FIELDS[ind], value) for
                                      ind, value in enumerate(result[4:]))))
    return ret


def get_keys(*args, **kwargs):
    return tuple(tuple(row[0:4]) for row in get(*args, **kwargs))


def get_experiment_ids(conn, experiment_names):
    """
    Return:
        dict: {experiment_name: experiment_ids}
    """
    ret = conn.cursor().execute(
        'SELECT name, experiment_id FROM experiments WHERE name IN '
        '(%s)' % (', '.join(['?'] * len(experiment_names))),
        experiment_names).fetchall()
    return dict((exp_name,
                 [exp_id for name, exp_id in ret if name == exp_name]) for
                exp_name in set(x[0] for x in ret))


def get_experiment_names(conn, experiment_ids):
    """
    Return:
        dict: {experiment_id: experiment_name}
    """
    ret = conn.cursor().execute(
        'SELECT experiment_id, name FROM experiments WHERE experiment_id IN '
        '(%s)' % (', '.join(['?'] * len(experiment_ids))),
        experiment_ids).fetchall()
    return dict((x, y) for x, y in ret)


def get_conn(db_file):
    """Return database connection.

    Creates profiling directory and database file if not present.

    Returns:
        sqlite3.Connection

    """
    if not os.path.exists(db_file):
        conn = sqlite3.connect(db_file)
        print 'Creating results database.'
        conn.cursor().execute(
            'CREATE TABLE experiments('
            'experiment_id TEXT PRIMARY KEY, '
            'name TEXT, '
            'options TEXT)')
        conn.cursor().execute(
            'CREATE TABLE results('
            'platform TEXT, '
            'version_id TEXT, '
            'experiment_id TEXT, '
            'run_name TEXT, '
            '%s)' % (', '.join('%s FLOAT' % i for i in RESULT_FIELDS)))
        conn.commit()
    else:
        conn = sqlite3.connect(db_file)
    return conn


def add(conn, results, experiments):
    args = []
    for platform, version_id, experiment_id, run_name, result_dict in results:
        exp_results = (result_dict.get(metric, None) for metric in
                       RESULT_FIELDS)
        args.append((platform, version_id, experiment_id, run_name) +
                    tuple(exp_results))
    stmt = 'INSERT INTO results VALUES(%s)' % ', '.join(
        (4 + len(prof.METRICS)) * ['?'])
    with conn:  # Commits automatically if successfull.
        conn.cursor().executemany(stmt, args)

    used_experiments = [filter_experiment(experiments, experiment_id) for
                        experiment_id in set(result[2] for result in results)]
    _sync_experiments(conn, experiments=experiments)


def remove(*args, **kwargs):
    kwargs['operator'] = 'SELECT'
    changes = get_keys(*args, **kwargs)

    kwargs['operator'] = 'DELETE'
    _results_call(*args, **kwargs)

    _sync_experiments(args[0], experiment_ids=[r[2] for r in changes])


def print_result(conn, platform, versions, experiment, quick_analysis,
                 markdown=False):
    prof_results = get_dict(
        conn,
        platform,
        [version['id'] for version in versions],
        experiment['id'],
        sort=True)

    # TODO!?
    #metrics = sorted(get_metrics_for_experiment(experiment, prof_results,
    #                                            quick_analysis=quick_analysis))
    metrics = analysis.get_consistent_metrics(prof_results, quick_analysis)

    # Make header rows.
    table = [['Version', 'Run'] + [analysis.get_metric_title(metric) for
                                   metric in sorted(metrics)]]
    table.append([None] * len(table[0]))  # Header underline.

    for (_, version_id, _, run_name), result_fields in prof_results:
        row = [version_id, run_name]
        for metric in metrics:
            try:
                row.append(result_fields[metric])
            except KeyError:
                raise Exception(  # TODO ResultsException?
                    'Could not make results table as results are incomplete. '
                    'Metric "%s" missing from %s:%s at version %s' % (
                        metric, experiment['name'], run_name, version_id
                    ))
        table.append(row)

    kwargs = {'transpose': not quick_analysis}
    if markdown:  # Move into print_table in the long run?
        kwargs.update({'seperator': ' | ', 'border': '|', 'headers': True})
    _write_table(table, **kwargs)


def _write_table(table, transpose=False, seperator = '  ', border='',
                 headers=False):  # TODO: Rename or whatever?
    """Print a 2D list as a table.

    None values are printed as hyphens, use '' for blank cells.
    """
    if transpose:
        table = map(list, zip(*table))
    if not table:
        return
    for row_no in range(len(table)):
        for col_no in range(len(table[0])):
            cell = table[row_no][col_no]
            if cell is None:
                table[row_no][col_no] = []
            else:
                table[row_no][col_no] = str(cell)

    col_widths = []
    for col_no in range(len(table[0])):
        col_widths.append(
            max([len(table[row_no][col_no]) for row_no in range(len(table))]))

    if headers:
        table = [table[0], [[]] * len(table[0])] + table[1:]

    for row_no in range(len(table)):
        for col_no in range(len(table[row_no])):
            if col_no != 0:
                sys.stdout.write(seperator)
            else:
                if border:
                    sys.stdout.write(border + ' ')
            cell = table[row_no][col_no]
            if type(cell) is list:
                sys.stdout.write('-' * col_widths[col_no])
            else:
                sys.stdout.write(cell + ' ' * (col_widths[col_no] - len(cell)))
            if col_no == len(table[row_no]) - 1:
                if border:
                    sys.stdout.write(' ' + border)
        sys.stdout.write('\n')


def print_list(conn, platforms, version_ids, experiment_ids):
    # Get (platform, version_id, experiment_id) keys from the results DB.
    prof_results = set(x[0:3] for x in get_keys(
        conn,
        platforms or None,
        version_ids or None,
        experiment_ids or None))

    # Get dictionary of {experiment_id: experiment_name} pairs.
    exp_name_dict = get_experiment_names(
        conn,
        list(set([result[2] for result in prof_results])))

    experiments = prof.get_experiments(set(exp_name_dict.values()),
                                       load_config=False)

    # Make table from results.
    table = [['Experiment Name', 'Experiment ID', 'Platform', 'Version ID'],
             [None, None, None, None]]
    previous = None
    for platform, version_id, experiment_id in sorted(prof_results,
                                                      _results_sorter):
        # Get the experiment name.
        experiment_name = exp_name_dict[experiment_id]
        # Put an asterix infront of the current version.
        experiment = filter_experiment(experiments, experiment_name, 'name')
        if experiment['id'] == experiment_id:
            experiment_id = '* %s' % experiment_id
        else:
            experiment_id = '  %s' % experiment_id
        row = []
        if previous:
            # Treat the table as a tree, don't repeat entries vertically.
            flag = True
            for ind, token in enumerate((
                    experiment_name, experiment_id, platform, version_id)):
                if flag and previous[ind] == token:
                    row.append('')
                else:
                    flag = False
                    row.append(token)
        else:
            row = [experiment_name, experiment_id, platform, version_id]
        table.append(row)
        previous = (experiment_name, experiment_id, platform, version_id)

    # Print table to stdout.
    _write_table(table)


def filter_experiment(experiments, value, field='id'):  # TODO: Use me!
    """Return the experiment for which the value matches the field.

    Args:
        experiments (list): List of experiment dictionaries.
        value (dynamic): The value to return the experiment for (e.g. the
            experiment id).
        field (str): The field to check against (e.g. 'id').

    Returns:
        dict: Experiment dictionary.

    Raises:
        IndexError: In the even that a matching experiment is not found.

    """
    for experiment in experiments:
        if experiment[field] == value:
            return experiment
    raise IndexError()


def get_experiment_options(experiment):
    options = {}
    for key in ['analysis', 'x-axis']:
        if key in experiment['config']:
            options[key] = experiment['config'][key]
    return options


class TestAddResult(unittest.TestCase):

    def setUp(self):
        self.conn = get_conn(tempfile.mktemp())
        add(self.conn,
            [
                ('a', 'b', 'c', 'd', {}),
                ('a', 'g', 'e', 'd', {}),
                ('f', 'b', 'e', 'd', {})
            ],
            [
                {'id': 'c', 'name': 'C', 'config': {}},
                {'id': 'e', 'name': 'E', 'config': {}}
            ]
        )

    def test_result_added(self):
        curr = self.conn.cursor()
        curr.execute('SELECT * FROM results')
        self.assertEqual(
            curr.fetchall(),
            [
                (u'a', u'b', u'c', u'd') + (None,) * len(RESULT_FIELDS),
                (u'a', u'g', u'e', u'd') + (None,) * len(RESULT_FIELDS),
                (u'f', u'b', u'e', u'd') + (None,) * len(RESULT_FIELDS)
            ]
        )

    def test_experiment_added(self):
        curr = self.conn.cursor()
        curr.execute('SELECT * FROM experiments')
        self.assertEqual(
            curr.fetchall(),
            [
                (u'c', u'C', '{}'),
                (u'e', u'E', '{}'),
            ]
        )

    def test_modified_experiment_result_added(self):
        add(self.conn,
            [
                ('f', 'g', 'h', 'd', {})
            ],
            [
                {'id': 'h', 'name': 'C', 'config': {}}
            ]
        )
        curr = self.conn.cursor()
        curr.execute('SELECT * FROM results')
        self.assertEqual(
            curr.fetchall(),
            [
                (u'a', u'b', u'c', u'd') + (None,) * len(RESULT_FIELDS),
                (u'a', u'g', u'e', u'd') + (None,) * len(RESULT_FIELDS),
                (u'f', u'b', u'e', u'd') + (None,) * len(RESULT_FIELDS),
                (u'f', u'g', u'h', u'd') + (None,) * len(RESULT_FIELDS)
            ]
        )

    def test_modified_experiment_experiment_added(self):
        add(self.conn,
            [
                ('f', 'g', 'h', 'd', {})
            ],
            [
                {'id': 'h', 'name': 'C', 'config': {}}
            ]
        )
        curr = self.conn.cursor()
        curr.execute('SELECT * FROM experiments')
        self.assertEqual(
            curr.fetchall(),
            [
                (u'c', u'C', '{}'),
                (u'e', u'E', '{}'),
                (u'h', u'C', '{}'),
            ]
        )


class TestRemoveResult(unittest.TestCase):

    def setUp(self):
        self.conn = get_conn(tempfile.mktemp())
        add(self.conn,
            [
                ('a', 'b', 'c', 'd', {}),
                ('a', 'b', 'e', 'd', {})
            ],
            [
                {'id': 'c', 'name': 'C', 'config': {}},
                {'id': 'e', 'name': 'E', 'config': {}}
            ]
        )
        remove(self.conn, experiment_ids=['e'])

    def test_result_removed(self):
        curr = self.conn.cursor()
        curr.execute('SELECT experiment_id FROM results')
        self.assertEqual(curr.fetchall(), [(u'c',)])

    def test_experiment_removed(self):
        curr = self.conn.cursor()
        curr.execute('SELECT experiment_id FROM experiments')
        self.assertEqual(curr.fetchall(), [(u'c',)])


class TestGetResult(unittest.TestCase):

    def setUp(self):
        self.conn = get_conn(tempfile.mktemp())
        add(self.conn,
            [
                ('a', 'b', 'c', 'd', {}),
                ('a', 'g', 'e', 'd', {}),
                ('f', 'b', 'e', 'd', {})
            ],
            [
                {'id': 'c', 'name': 'C', 'config': {}},
                {'id': 'e', 'name': 'E', 'config': {}}
            ]
        )

    def test_get_all(self):
        self.assertEqual(
            get(self.conn),
            [
                (u'a', u'b', u'c', u'd') + (None,) * len(RESULT_FIELDS),
                (u'a', u'g', u'e', u'd') + (None,) * len(RESULT_FIELDS),
                (u'f', u'b', u'e', u'd') + (None,) * len(RESULT_FIELDS)
            ]
        )

    def test_get_by_platform(self):
        self.assertEqual(
            get(self.conn, platforms=['a']),
            [
                (u'a', u'b', u'c', u'd') + (None,) * len(RESULT_FIELDS),
                (u'a', u'g', u'e', u'd') + (None,) * len(RESULT_FIELDS),
            ]
        )
        self.assertEqual(
            get(self.conn, platforms=['f']),
            [
                (u'f', u'b', u'e', u'd') + (None,) * len(RESULT_FIELDS)
            ]
        )

    def test_get_by_version(self):
        self.assertEqual(
            get(self.conn, version_ids=['b']),
            [
                (u'a', u'b', u'c', u'd') + (None,) * len(RESULT_FIELDS),
                (u'f', u'b', u'e', u'd') + (None,) * len(RESULT_FIELDS)
            ]
        )
        self.assertEqual(
            get(self.conn, version_ids=['g']),
            [
                (u'a', u'g', u'e', u'd') + (None,) * len(RESULT_FIELDS),
            ]
        )

    def test_get_by_experiment(self):
        self.assertEqual(
            get(self.conn, experiment_ids=['c']),
            [
                (u'a', u'b', u'c', u'd') + (None,) * len(RESULT_FIELDS)
            ]
        )
        self.assertEqual(
            get(self.conn, experiment_ids=['e']),
            [
                (u'a', u'g', u'e', u'd') + (None,) * len(RESULT_FIELDS),
                (u'f', u'b', u'e', u'd') + (None,) * len(RESULT_FIELDS)
            ]
        )


if __name__ == '__main__':
    unittest.main()
