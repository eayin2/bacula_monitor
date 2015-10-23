#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
import os
import psycopg2
import sys
from subprocess import Popen,PIPE
import fnmatch
import os
from collections import defaultdict

import logging
logger = logging.getLogger(__name__)

#### Config
# path to the job configs
jobs_path = "/etc/bareos/bareos-dir.d/jobs"
# file path to jobdefs.conf
jobdefs_path = "/etc/bareos/bareos-dir.d/jobs/jobdefs.conf"

#### Functions
def fill_pools_to_client(jobdef_name, value_list, jobs_dict, client_pool_dict, client=None):
    """ parses jobdefs.conf and returns values for given keys packed in a dictionary. """
    with open (jobdefs_path, "r") as myfile:
        jobdefs_parsed = parse_bareos(myfile)
    value_dict = defaultdict()
    for dict in jobdefs_parsed:
        dict = {k.lower():v for k,v in dict.items()}
        if dict["name"].lower().replace('"', '') == jobdef_name.lower().replace('"',''):
            for value in value_list:
                try:
                    if client:
                        print(dict[value].replace("'", ""))
                        print(dict[value])
                        client = re.sub('["\']', '', client)
                        client_pool_dict[ client ].add(dict[value].replace("'", ""))
                    else:
                        name= re.sub('[(){}<>]', '', name)
                        client = re.sub('["\']', '', dict["client"])
                        client_pool_dict[ client ].add(dict[value].replace("'", ''))

                except Exception as err:
                    print(err)
                    print("jobdefs has dict[%s] neither." % value)
    return client_pool_dict

def jobdefs_values(jobdef_name, value_list):
    """ parses jobdefs.conf and returns values for given keys packed in a dictionary. """
    with open (jobdefs_path, "r") as myfile:
        jobdefs_parsed = parse_bareos(myfile)
    value_dict = defaultdict()
    for dict in jobdefs_parsed:
        dict = {k.lower():v for k,v in dict.items()}
        if dict["name"].lower().replace('"', '') == jobdef_name.lower().replace('"',''):
            for value in value_list:
                try:
                    value_dict[value] = dict[value]
                except Exception as err:
                    print(err)
                    print("jobdefs has dict[%s] neither." % value)
    return value_dict

def parse_bareos(lines):
    """ can parse bareos configs and returns a list of each config segment packed in one dictionary. """
    parsed = []
    obj = None
    for line in lines:
        line, hash, comment = line.partition('#')
        line = line.strip()
        if not line:
            continue

        m = re.match(r"(\w+)\s*{", line)
        if m:
            # Start a new object
            if obj is not None:
                raise Exception("Nested objects!")
            obj = {'thing': m.group(1)}
            parsed.append(obj)
            continue

        m = re.match(r"\s*}", line)
        if m:
            # End an object
            obj = None
            continue

        m = re.match(r"\s*([^=]+)\s*=\s*(.*)$", line)
        if m:
            # An attribute
            key, value = m.groups()
            obj[key.strip()] = value.rstrip(';')
            continue
    return parsed



def client_pool_map():
    """ returns a dictionary of all pools that a client is associated to in the bareos jobs config."""
    files = []

    for root, dirnames, filenames in os.walk(jobs_path):
        for filename in fnmatch.filter(filenames, '*.conf'):
            file_path = os.path.join(root, filename)
            if file_path == jobdefs_path:
                continue
            files.append(os.path.join(root, filename))

    client_pool_dict = defaultdict(set)
    copy_dependency_dict = defaultdict(set)
    for file in files:
        with open (file, "r") as myfile:
            parsed_conf = parse_bareos(myfile)
        for d in parsed_conf:
            d = {k.lower():v for k,v in d.items()}

            if "pool" in d and "client" in d:
                 print(d["client"])
                 print(d["pool"])
                 print(client_pool_dict)
                 client_pool_dict[d["client"]].add(d["pool"])

            elif "jobdefs" in d:
                jobdef_name = d["jobdefs"].lower()

                if "client" in d and not "pool" in d:
                    client_pool_dict = fill_pools_to_client(jobdef_name, ["pool", "incremental backup pool", "full backup pool"], d, client_pool_dict, d["client"])

                elif not "client" in d and "pool" in d:

                    # Copy Job
                    if "type" in d:
                        if d["type"].lower() == "copy":
                            copy_dependency_dict[dict["pool"]].add(d["next pool"])

                    elif jobdefs_values(jobdef_name, ['type'])["type"].lower() == "copy":
                        copy_dependency_dict[d["pool"]].add(d["next pool"])

                    # Backup Job
                    else:
                        client_pool_dict = fill_pools_to_client(jobdef_name, ["pool", "incremental backup pool", "full backup pool"], d, client_pool_dict)

                elif not "client" in d and not "pool" in d:
                    client_pool_dict = fill_pools_to_client(jobdef_name, ["pool", "incremental backup pool", "full backup pool"], d, client_pool_dict)

            else:
                print("no jobdefs, pool and client info.")
    return client_pool_dict, copy_dependency_dict
