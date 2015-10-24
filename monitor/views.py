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
from collections import defaultdict, OrderedDict
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
    config_copy_dep = dict(config_copy_dep)
    con = None
    try:
        con = psycopg2.connect(database='bareos', user='bareos', host='phserver01')
        cur = con.cursor()
        cur.execute("SELECT c.name, p.name, j.jobbytes, j.realendtime, j.starttime, j.jobfiles \
                     FROM client c \
                     LEFT JOIN LATERAL ( \
                       SELECT DISTINCT ON (j.poolid, j.clientid) j.jobbytes, j.realendtime, j.starttime, j.jobfiles, j.poolid \
                       FROM job j \
                       WHERE j.clientid = c.clientid AND j.jobstatus='T' AND j.level IN ('F', 'I', 'D') AND j.type IN ('B', 'C') \
                       ORDER BY j.clientid, j.poolid, j.realendtime DESC \
                     ) j ON TRUE \
                     LEFT JOIN pool p ON p.poolid = j.poolid;")

        tuples = cur.fetchall()
        jobs = defaultdict(dict)
        # jobs dict looks like: { client1 : { pool1 : [ jobbytes, realendtime, .. ], pool2 : [..] }, client2: { ... } }
        clients_pools_dict = defaultdict(list)
        for t in tuples:
            logger.debug(t)
            client = t[0]
            pool = t[1]
            pool_sub_dict = defaultdict(list)
            pool_list = list()
            jobbytes = t[2]
            realendtime = t[3]
            starttime = t[4]
            try:
                duration = realendtime - starttime
            except:
                continue
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
            pool_list = [jobgigabytes, endtime, minutes, t[5], timeout]
            jobs[client][pool] = pool_list
    except ValueError as err:
        logger.debug(err)
        logger.debug("Error in view.")
    # converting back to dict so template can print it
    jobs = dict(jobs)
    jobs = OrderedDict(sorted(jobs.items()))
    # here we sort our copy pool dependency dictionary before filling it into the config_client_pool dictionary.
    for key, li in config_copy_dep.items():
        config_copy_dep[key] = sorted(li)
    # here we add copy pools that are associated to a pool to the client's pool dictionary.
    config_copy_dep = OrderedDict(sorted(config_copy_dep.items()))
    for cpk, cpv in config_client_pool.items():
        for cdk, cdv in config_copy_dep.items():
            if cdk in cpv:
                for cdv2 in cdv:
                    config_client_pool[cpk].add(cdv2)
    # Sorting in the end so that set() doesnt get converted to list()
    for key, li in config_client_pool.items():
        config_client_pool[key] = sorted(li)
    config_client_pool = OrderedDict(sorted(config_client_pool.items()))
    return render_to_response('monitor/index.html', {'jobs' : jobs, 'jobs_should': config_client_pool, 'copy_dep': config_copy_dep}, context_instance=RequestContext(request))
