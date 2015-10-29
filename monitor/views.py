from django.shortcuts import render
from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response
import logging
logger = logging.getLogger(__name__)
import datetime
import re
import os
import psycopg2
import sys
from subprocess import Popen,PIPE
from collections import defaultdict, OrderedDict
from monitor.functions import client_pool_map, host_up, validate_yaml
from six import iteritems
# Validating YAML and retrieving timeout setting. if there's no timeout setting we use a default value here.
yaml_parsed = validate_yaml()
try:
    _timeouts = yaml_parsed["timeouts"]
except:
    # setting timeouts as integer. later our code checks whether _timeouts is a dict or integer.
    _timeouts = 30

def default_to_regular(d):
    if isinstance(d, defaultdict):
        d = {k: default_to_regular(v) for k, v in d.iteritems()}
    return d

def monitor(request):
    jobs_config, config_copy_dep = client_pool_map()
    config_copy_dep = dict(config_copy_dep)
    con = None
    try:
        con = psycopg2.connect(database='bareos', user='bareos', host='phserver01')
        con.set_session(readonly=True)
        cur = con.cursor()
        cur.execute("SELECT c.name, p.name, j.jobbytes, j.realendtime, j.starttime, j.jobfiles, f.fileset \
                     FROM client c \
                     LEFT JOIN ( \
                       SELECT DISTINCT ON (j.clientid, j.poolid, j.filesetid) \
                       j.jobbytes, j.realendtime, j.clientid, j.poolid, j.starttime, j.jobfiles, j.type, j.level, j.jobstatus, j.filesetid \
                       FROM job j \
                       WHERE j.jobstatus IN ('T', 'W') AND j.level IN ('F', 'I', 'D') AND j.type IN ('B', 'C') \
                       ORDER BY j.clientid, j.poolid, j.filesetid, j.realendtime DESC \
                     ) j ON j.clientid = c.clientid \
                     LEFT JOIN pool p ON p.poolid = j.poolid \
                     LEFT JOIN fileset f ON f.filesetid = j.filesetid;")  # (12)
        tuples = cur.fetchall()
        jobs = defaultdict(lambda: defaultdict(defaultdict))
        clients_pools_dict = defaultdict(list)  # (0)
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
                for tk, tv in _timeouts.iteritems():
                    if pool in tv:  # checking if pool is in tv (list of pools from _timeouts)
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
    for key, li in config_copy_dep.iteritems(): # (9)
        config_copy_dep[key] = sorted(li)
    config_copy_dep = OrderedDict(sorted(config_copy_dep.iteritems())) # (10)

    # adding "copy dependend pools" to "jobs config pools"
    for cck, ccv in jobs_config.iteritems():  # config client key/val
        for cfk, cfv in ccv.iteritems(): # config fileset
            for cdk, cdv in config_copy_dep.iteritems(): # config dep is just 1 level dict like so: {'Full-LT': ['Full-Copy-LT', 'Incremental-Copy-LT'], ...}
                if cdk in cfv:  # cfv is list of pools associated to fileset key
                    for cde in cdv: # copy dep element
                        jobs_config[cck][cfk].add(cde)  # adding dep pool to list client_fileset pools.
    for jck, jcv in jobs_config.iteritems():
        for cfk, cfv in jcv.iteritems():
            jobs_config[jck][cfk] = sorted(cfv)
    jobs_config = OrderedDict(sorted(jobs_config.iteritems())) # (8)
    hosts = dict(host_up())  # (5)
    # setting missing pools to value 0.
    for jck, jcv in jobs.iteritems(): # (4)
        for cck, ccv in jobs_config.iteritems():  # config_client_key/val
            if jck == cck: # (7)
                for jfk, jfv in jcv.iteritems():
                    for cfk, cfv in ccv.iteritems():  # cfv is a list of all pools that "should" exist for each client's fileset.
                        if jfk == cfk:  # if not checked that jfk == cfk, we would get pools marked as missing for filesets though they aren't.
                            for cfe in cfv: # (1)
                                if not cfe in jfv: # (2)
                                    jobs[jck][jfk][cfe] = 0 # (6)
    jobs = default_to_regular(jobs)  # (5)
    # Sorting
    for jck, jcv in jobs.iteritems():
        for jfk, jfv in jcv.iteritems():
            jobs[jck][jfk] = OrderedDict( sorted( jobs[jck][jfk].iteritems() ) )
    jobs = OrderedDict( sorted( jobs.iteritems() ) )  # (3)
    return render_to_response('monitor/index.html', {'jobs' : jobs, 'hosts' : hosts }, context_instance=RequestContext(request))


# Notes:
# (0) jobs dict looks like: { client1 : { pool1 : [ jobbytes, realendtime, .. ], pool2 : [..] }, client2: { ... } }
# (1) jcv looks as such: ['Full-LT', 'Full-LT-Copies-01', 'Full-LT-Copies-02', 'Incremental-LT', 'Incremental-LT-Copies-01', 'Incremental-LT-Copies-02']
# (2) jfv looks like: defaultdict(None, {'Full-ST': [181, '03.10.15 16:30', 30, 116172, 0], 'Incremental-ST': [2, '24.10.15 18:19', 0, 78, 0]})
# (3) a dictionary will always return keys/values in random order, that's why we have to use an "OrderedDict"
# (4) comparing jobs_config with jobs dictionary in this view instead of in the template, that keeps the template cleaner and in general easier to write.
# (5) converting back to dict so template can print it
# (6) set it to 0, not sure if it cascades with None
# (7) if job client key (is) == config client key (should)
# (8) Sorting in the end, so that set() doesnt get converted to list(), in order to have add() method available.
# (9) here we sort our copy pool dependency dictionary before filling it into the client_pool dictionary
# (10) here we add copy pools that are associated to a pool to the config client's pool dictionary (aka jobs_should).
# (11) note for myself: i set Copies-01 to 60 days, so i can easier see if i can do a disaster Copie-02 backup from relatively new Copies.
# (12) jobstatus 'W' means terminated successful but with warnings in bareos. Iam not sure if bacula has the same jobstatus code too. bacula has T (successful) though.
