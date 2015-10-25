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
# path to the job configs. I tested it with bareos, so i the bareos config path. For bacula put it in the approriate path.
jobs_path = "/etc/bareos/bareos-dir.d/jobs"
# file path to jobdefs.conf
jobdefs_path = "/etc/bareos/bareos-dir.d/jobs/jobdefs.conf"
# Path to your client config.
client_config = "/etc/bareos/bareos-dir.d/clients.conf"

#### Functions
def fill_pools_to_client(jobdef_name, value_list, jobs_dict, config_client_pool, client=None):
    """ parses jobdefs.conf and returns values for given keys packed in a dictionary. """
    with open (jobdefs_path, "r") as myfile:
        jobdefs_parsed = parse_bacula(myfile)
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
                        config_client_pool[ client ].add(dict[value].replace("'", ""))
                    else:
                        name= re.sub('[(){}<>]', '', name)
                        client = re.sub('["\']', '', dict["client"])
                        config_client_pool[ client ].add(dict[value].replace("'", ''))

                except Exception as err:
                    print(err)
                    print("jobdefs has dict[%s] neither." % value)
    return config_client_pool

def jobdefs_values(jobdef_name, value_list):
    """ parses jobdefs.conf and returns values for given keys packed in a dictionary. """
    with open (jobdefs_path, "r") as myfile:
        jobdefs_parsed = parse_bacula(myfile)
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

def parse_bacula(lines):
    """ can parse bacula configs and returns a list of each config segment packed in one dictionary. """
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
    """ returns a dictionary of all pools that a client is associated to in the bacula jobs config."""
    files = []

    for root, dirnames, filenames in os.walk(jobs_path):
        for filename in fnmatch.filter(filenames, '*.conf'):
            file_path = os.path.join(root, filename)
            if file_path == jobdefs_path:
                continue
            files.append(os.path.join(root, filename))

    config_client_pool = defaultdict(set)
    config_copy_dep = defaultdict(set)
    for file in files:
        with open (file, "r") as myfile:
            parsed_conf = parse_bacula(myfile)
        for d in parsed_conf:
            d = {k.lower():v for k,v in d.items()}

            if "pool" in d and "client" in d:
                 print(d["client"])
                 print(d["pool"])
                 print(config_client_pool)
                 config_client_pool[d["client"]].add(d["pool"])

            elif "jobdefs" in d:
                jobdef_name = d["jobdefs"].lower()

                if "client" in d and not "pool" in d:
                    config_client_pool = fill_pools_to_client(jobdef_name, ["pool", "incremental backup pool", "full backup pool"], d, config_client_pool, d["client"])

                elif not "client" in d and "pool" in d:

                    # Copy Job
                    if "type" in d:
                        if d["type"].lower() == "copy":
                            config_copy_dep[dict["pool"]].add(d["next pool"])

                    elif jobdefs_values(jobdef_name, ['type'])["type"].lower() == "copy":
                        config_copy_dep[d["pool"]].add(d["next pool"])

                    # Backup Job
                    else:
                        config_client_pool = fill_pools_to_client(jobdef_name, ["pool", "incremental backup pool", "full backup pool"], d, config_client_pool)

                elif not "client" in d and not "pool" in d:
                    config_client_pool = fill_pools_to_client(jobdef_name, ["pool", "incremental backup pool", "full backup pool"], d, config_client_pool)

            else:
                print("no jobdefs, pool and client info.")
    return config_client_pool, config_copy_dep  # (1)

def hosts():
    """Parses config and returns all clients and associated hostnames."""
    with open (client_config, "r") as myfile:
        client_parsed = parse_bacula(myfile)
    # For dictionaries in list of dict.
    _hosts = defaultdict(set)
    for d in client_parsed:
        # Making sure we got the right config segment.
        if d["thing"].lower() == "client":
            for dk, dv in d.items():
                if dk.lower() == "name":
                    name = dv
                elif dk.lower() == "address":
                    address = dv
            _hosts[ name ].add( address )
    return _hosts

def host_up():
    """Checks if 9102 is open and returns dictionary of available hosts."""
    # bacula requires port 9102 be opened on the file daemon.
    _hosts = hosts()
    for hk, hv in _hosts.items():
        p2 = Popen([ "/usr/bin/netcat", "-z", "-v", "-w", "2", list(hv)[0], "9102" ], stdout=PIPE, stderr=PIPE, universal_newlines=True)
        out, err = p2.communicate()
        if "succeeded" in err:
            print('y')
            _hosts[ hk ].add(1)
        else:
            print('n')
            _hosts[ hk ].add(0)
    return _hosts
print(host_up())

# (1) don't sort the dictionaries here yet, because we still need the set() values.

