from django.shortcuts import render
from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response
import logging
logger = logging.getLogger(__name__)
import datetime
import re
import pprint
import os
import psycopg2
import sys
from subprocess import Popen,PIPE
from collections import defaultdict
from monitor.functions import client_pool_map
#### Config
# timeout for jobs (in days). marked as "OLD" if exceeded timeout.
_timeout = 60

#### Implement
# if short term older than 4 weeks mark red
# if long term older than 3 months mark red

#### Developer-Info
# Pools:
# Full-LT-Copies-01, Full-LT-Copies-02, Incremental-ST, Incremental-LT, Full-ST, Full-LT
# abstracted: Shortterm, Longterm, Full Longterm Copy
# Clients:
# phserver01-fd, phpc01lin-fd, phlap01linw-fd, phlap01winw-fd, phlap02linw-fd, pharm01-fd, mapc01-fd
# => List by clients and then present 2 latest job for each client pool within the client's table
# data structure:
# { a : { b : [1, 2, 3],
#         c : [4, 5, 6],
#         d : [7, 8, 9]
#       },
#  aa : { bb : [11, 22, 33],
#         cc : [44, 55, 66]
#       }
# }
# - no need to show type because pool name implies type
# - no need to show 'T' for successful job, because only T is retrieved.
# - no need to show/select full or inc type either, bcs pool name implies it too.

def monitor(request):
    config_client_pool, config_copy_dep = client_pool_map()
    config_client_pool = dict(config_client_pool)
    config_copy_dep = dict(config_copy_dep)
    # import pdb
    # pdb.set_trace()
    con = None
    try:
        con = psycopg2.connect(database='bareos', user='bareos', host='phserver01')
        cur = con.cursor()
        cur.execute("SELECT c.name, p.name, j.jobbytes, j.realendtime, j.starttime, j.jobfiles \
                 FROM client c, pool p, LATERAL(SELECT * FROM job j WHERE j.clientid = c.clientid AND \
                 j.jobstatus='T' AND j.level IN ('F', 'I', 'D') AND j.type IN ('B', 'C') AND p.poolid=j.poolid \
                 ORDER BY j.realendtime DESC LIMIT 2) j;")
        cur.execute("SELECT c.name, p.name, j.jobbytes, j.realendtime, j.starttime, j.jobfiles \
                 FROM client c, pool p, LATERAL(SELECT * FROM job j WHERE j.clientid = c.clientid AND \
                 j.jobstatus='T' AND j.level IN ('F', 'I', 'D') AND j.type IN ('B', 'C') AND p.poolid=j.poolid \
                 ORDER BY j.realendtime DESC LIMIT 2) j;")
        tuples = cur.fetchall()
        jobs = defaultdict(dict)
        clients_pools_dict = defaultdict(list)
        for tuple in tuples:
            client = tuple[0]
            pool = tuple[1]
            pool_sub_dict = defaultdict(list)
            pool_list = list()
            jobbytes = tuple[2]
            realendtime = tuple[3]
            starttime = tuple[4]
            duration = realendtime - starttime
            seconds = duration.total_seconds()
            minutes = int((seconds % 3600) // 60)
            endtime = realendtime.strftime("%d.%m.%y %H:%M")
            # grob aufrunden
            jobgigabytes = int(jobbytes/1000000000)
            current_time = datetime.datetime.now()
            timeout_max = datetime.timedelta(days=_timeout)
            logger.debug( ( current_time - realendtime )  )
            logger.debug( timeout_max )
            if ( current_time - realendtime ) > timeout_max:
                timeout = 1
            else:
                timeout = 0
            pool_list = [jobgigabytes, endtime, minutes, tuple[5], timeout]
            clients_pools_dict[pool] = pool_list
            jobs[client] = dict(clients_pools_dict)
    except ValueError as err:
        logger.debug(err)
        logger.debug("Error in view.")
    # converting back to dict so template can print it
    logger.debug("now:")
    logger.debug(jobs)
    jobs = dict(jobs)
    return render_to_response('monitor/index.html', {'jobs' : jobs, 'jobs_should': config_client_pool, 'copy_dep': config_copy_dep}, context_instance=RequestContext(request))
