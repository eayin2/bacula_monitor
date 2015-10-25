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
from monitor.functions import client_pool_map, host_up
#### Config
# timeout for jobs (in days). marked as "OLD" if exceeded timeout.
#_timeout = 60
# format: days : [pool_name1, ...]
_timeouts = { 90 : [ "Full-LT", "Incremental-LT"],
              30 : [ "Full-ST", "Incremental-ST"],
              60 : [ "Full-LT-Copies-01", "Incremental-LT-Copies-01"],
             150 : [ "Full-LT-Copies-02", "Incremental-LT-Copies-02"] }
              # note for myself: i set Copies-01 to 60 days, so i can easier see if i can do a disaster Copie-02 backup
              # from relatively new Copies.

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

def default_to_regular(d):
    if isinstance(d, defaultdict):
        d = {k: default_to_regular(v) for k, v in d.items()}
    return d

def monitor(request):
    config_client_pool, config_copy_dep = client_pool_map()
    config_copy_dep = dict(config_copy_dep)
    con = None
    try:
        con = psycopg2.connect(database='bareos', user='bareos', host='phserver01')
        cur = con.cursor()
        # Notice that jobstatus 'W' means terminated successful but with warnings in bareos. Iam not sure if bacula has the same jobstatus code too. bacula has T (successful) though.
        cur.execute("\
SELECT c.name, p.name, j.jobbytes, j.realendtime, j.starttime, j.jobfiles, f.fileset \
FROM client c \
LEFT JOIN ( \
  SELECT DISTINCT ON (j.clientid, j.poolid, j.filesetid) \
    j.jobbytes, j.realendtime, j.clientid, j.poolid, j.starttime, j.jobfiles, j.type, j.level, j.jobstatus, j.filesetid \
  FROM job j \
  WHERE j.jobstatus IN ('T', 'W') AND j.level IN ('F', 'I', 'D') AND j.type IN ('B', 'C') \
  ORDER BY j.clientid, j.poolid, j.filesetid, j.realendtime DESC \
) j ON j.clientid = c.clientid \
LEFT JOIN pool p ON p.poolid = j.poolid \
LEFT JOIN fileset f ON f.filesetid = j.filesetid;")

        tuples = cur.fetchall()
        jobs = defaultdict(lambda: defaultdict(defaultdict))
        # jobs dict looks like: { client1 : { pool1 : [ jobbytes, realendtime, .. ], pool2 : [..] }, client2: { ... } }
        clients_pools_dict = defaultdict(list)
        for t in tuples:
            client = t[0]
            fileset = t[6]
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
            if isinstance(_timeouts, int):
                timeout_max = datetime.timedelta(days=_timeouts)
                if ( current_time - realendtime ) > timeout_max:
                    timeout = 1
                else:
                    timeout = 0
            elif isinstance(_timeouts, dict):
                for tk, tv in _timeouts.items():
                    # checking if pool is in tv (list of pools from _timeouts)
                    if pool in tv:
                        timeout_max = datetime.timedelta(days=tk)
                        if ( current_time - realendtime ) > timeout_max:
                            timeout = 1
                        else:
                            timeout = 0
                        break
            pool_list = [jobgigabytes, endtime, minutes, t[5], timeout]
            jobs[client][fileset][pool] = pool_list
    except ValueError as err:
        logger.debug(err)
        logger.debug("Error in view.")
    # here we sort our copy pool dependency dictionary before filling it into the client_pool dictionary
    for key, li in config_copy_dep.items():
        config_copy_dep[key] = sorted(li)
    # here we add copy pools that are associated to a pool to the config client's pool dictionary (aka jobs_should).
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
    hosts = dict(host_up())  # (5)
    for jck, jcv in jobs.items(): # (4)
        for cck, ccv in config_client_pool.items():  # config_client_key/val
            if jck == cck: # (7)
                for jfk, jfv in jcv.items():
                    logger.debug(jfv)
                    for cce in ccv:  # (1)
                        if cce in jfv: # (2)
                            pass
                        else:
                            jobs[jck][jfk][cce] = 0 # (6)
    jobs = default_to_regular(jobs)  # (5)
#    for jck, jcv in jobs.items():
 #       for jfk, jfv in jcv.items():
  #          jobs[jfk] = sorted(jfv)
    logger.debug(jobs)
    for jck, jcv in jobs.items():
        for jfk, jfv in jcv.items():
            jobs[jck][jfk] = OrderedDict( sorted( jobs[jck][jfk].items() ) )
    jobs = OrderedDict( sorted( jobs.items() ) )  # (3)
    return render_to_response('monitor/index.html', {'jobs' : jobs, 'hosts' : hosts }, context_instance=RequestContext(request))


# Notes:
# (1) ccv looks as such: ['Full-LT', 'Full-LT-Copies-01', 'Full-LT-Copies-02', 'Incremental-LT', 'Incremental-LT-Copies-01', 'Incremental-LT-Copies-02']
# (2) jfv looks like: defaultdict(None, {'Full-ST': [181, '03.10.15 16:30', 30, 116172, 0], 'Incremental-ST': [2, '24.10.15 18:19', 0, 78, 0]})
# (3) a dictionary will always return keys/values in random order, that's why we have to use an "OrderedDict"
# (4) comparing config_client_pool with jobs dictionary in this view instead of in the template, that keeps the template cleaner and in general easier to write.
# (5) converting back to dict so template can print it
# (6) set it to 0, not sure if it cascades with None
# (7) if job client key (is) == config client key (should)

