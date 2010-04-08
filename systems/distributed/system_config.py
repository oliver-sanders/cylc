#!/usr/bin/python

#         __________________________
#         |____C_O_P_Y_R_I_G_H_T___|
#         |                        |
#         |  (c) NIWA, 2008-2010   |
#         | Contact: Hilary Oliver |
#         |  h.oliver@niwa.co.nz   |
#         |    +64-4-386 0461      |
#         |________________________|

# o SYSTEM CONFIG MODULE FOR THE CYLC SYSTEM DEFINITION DIRECTORY:
#  /home/oliverh/cylc/systems/distributed
# o REFER TO THE CYLC USER GUIDE FOR DOCUMENTATION OF CONFIG ITEMS. 
# o THIS FILE WAS AUTOGENERATED BY 'cylc configure' BUT WILL NOT
# BE OVERWRITTEN ON RECONFIGURATION UNLESS YOU FORCE IT. 

# Configured items are held in a dict (Python associative array): 
#   items[ 'item' ] = value.
# Note that some "values" are themselves lists or dicts.

from config import config
from task_list import task_list
from system_info import info
import logging  # for logging level
import os       # os.environ['HOME']

class system_config( config ):

    def __init__( self, sysname ):
        config.__init__( self, sysname )

        # system title
        # self.items[ 'system_title' ] = 'DEFAULT TITLE'

        # system task list
        self.items['task_list'] = task_list   # SEE task_list.py

        # list of legal startup hours, if this system is so restricted
        # e.g.: self.items['legal_startup_hours'] = [ 6 ]
        # or:   self.items['legal_startup_hours'] = [ 6, 18 ]

        # system info
        self.items['system_info']['info'] = info   # SEE system_info.py

        # add more descriptive information as you like, e.g.:
        # self.items[ 'system_info' ]['colours'] = 'red, blue, green'

        # task insertion groups, e.g:
        # self.items['task_groups']['foo'] = ['bar', 'baz']

        # default job submit method, e.g.:
        self.items['job_submit_method'] = 'background'

        # to override the default job submit method for specific tasks, e.g.:
        self.items['job_submit_overrides']['background_remote'] = \
                [ 'cold', 'forecast' ]

        # environment variables available to all tasks, can include
        # the registered system name, e.g.:
        user = os.environ['USER'] 
        self.items['environment']['CYLC_TMPDIR'] = '/tmp/' + user + '/' + sysname

        user = os.environ['USER'] 
        self.items['environment']['CYLC_REMOTE_TMPDIR'] = '/tmp/' + user + '/' + sysname + '-remote'

        # remote host on which to run the coldstart and forecast tasks
        self.items['environment']['SUPERCOMPUTER'] = '192.168.126.129'

# END OF FILE
