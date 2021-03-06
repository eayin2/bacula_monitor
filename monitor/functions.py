#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
import os
import sys
import os
import logging
import traceback
from subprocess import Popen,PIPE
from collections import defaultdict

import fnmatch
import yaml
import psycopg2
from six import iteritems
from voluptuous import Schema, Required, All, Length, Range, MultipleInvalid

logger = logging.getLogger(__name__)


def format_exception(e):
    """Usage: except Exception as e:
                  log.error(format_exception(e)) """
    exception_list = traceback.format_stack()
    exception_list = exception_list[:-2]
    exception_list.extend(traceback.format_tb(sys.exc_info()[2]))
    exception_list.extend(traceback.format_exception_only(sys.exc_info()[0], sys.exc_info()[1]))
    exception_str = "Traceback (most recent call last):\n"
    exception_str += "".join(exception_list)
    exception_str = exception_str[:-1]  # Removing the last \n
    return exception_str


def validate_yaml():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logger.debug(BASE_DIR)
    with open(os.path.join(BASE_DIR,"bm.conf"), 'r') as stream:
        yaml_parsed = yaml.load(stream)
    schema = Schema({
        Required('bacula_config_path'): str,
        Required('port'): int,
        "virtualenv": str,
        'timeouts': Schema({int: [str]}) # if not timeouts set, use default value
    })
    try:
        schema(yaml_parsed)
    except MultipleInvalid as e:
        exc = e
        raise AssertionError(e)
    return yaml_parsed
yaml_parsed = validate_yaml()
bacula_config_path = yaml_parsed["bacula_config_path"]
port = str(yaml_parsed["port"])


def bacula_config_files():
    """ returns all files found in bacula_config_path recursively. """
    files = []
    for root, dirnames, filenames in os.walk(bacula_config_path):
        for filename in fnmatch.filter(filenames, '*.conf'):
            file_path = os.path.join(root, filename)
            files.append(os.path.join(root, filename))
    return files

def config_values(d):
    """ tries to get values for mulitple keys and sets value None if key is not existent. keys and values are packed and returns as dict."""
    d = {k.lower():v for k,v in iteritems(d)}
    client = d.get("client", None)
    fileset = d.get("fileset", None)
    pool = d.get("pool", None)
    fbp = d.get("full backup pool", None)
    ibp = d.get("incremental backup pool", None)
    np = d.get("next pool", None)
    ty = d.get("type", None)
    cvl = {"client": client,
           "fileset": fileset,
           "pool": pool,
           "full backup pool": fbp,
           "incremental backup pool": ibp,
           "type": ty,
           "next pool": np}
    return cvl

def jobdefs_conf_values(jobdef_name):
    """ parses jobdefs.conf and returns values for keys defined in config_values()."""
    files = bacula_config_files()
    for file in files:
        with open (file, "r") as myfile:
            parsed_conf = parse_bacula(myfile)
        if not parsed_conf:  # excludes nested configs, which our parser can't parse.
            continue
        for d in parsed_conf:
            if d["name"].lower() == jobdef_name and d["resource"].lower() == "jobdefs":
                jcd = config_values(d)
    return jcd   # job config dict


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
                return None  # if file is nested, than skip it. (e.g. filesets.conf is nested, and we dont want to parse fileset resources.)
                # raise Exception("Nested objects!")
            obj = {'resource': m.group(1)}
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
    parsed = [{key.lower():val.replace('"',"") for key, val in iteritems(dict)} for dict in parsed]  # Removing any quote signs from values and applying lower() to all keys.
    return parsed


def client_pool_map():
    """ returns a dictionary of all pools that a client is associated to in the bacula jobs config and returns another dict containing all copy pool dependencies."""
    files = bacula_config_files()
    jobs_config = defaultdict(lambda: defaultdict(set))
    config_copy_dep = defaultdict(set)
    for file in files:
        with open (file, "r") as myfile:
            parsed_conf = parse_bacula(myfile)
        if not parsed_conf:
            continue
        for d in parsed_conf:
            if d["resource"].lower() == "job":
                done = False
                d = {k.lower():v for k,v in iteritems(d)}
                cvd = config_values(d) # config value dict
                if  "jobdefs" in d:  # (2)
                    jobdef_name = d["jobdefs"].lower()
                    jcd = jobdefs_conf_values(jobdef_name)  # jobdefs config dict
                else:
                    jcd = config_values(d)  # if no jobdefs then set jcd also to config values and when its compared to cvd then it doesnt differentiate from cvl.
                cvd.update({jck:jcv for jck, jcv in iteritems(jcd) if jcv})  # jobdefs config key (its just temp value dict, no nested things here)
                if cvd["fileset"] == None and cvd['type'].lower() == "copy":
                    config_copy_dep[d["pool"]].add(cvd["next pool"])  # above we added also next pool (if available) to the dict cvd
                    continue  # because we dont want fileset None-type in our jobs_config.
                elif cvd["client"] == None or cvd["fileset"] == None or cvd["pool"] == None and not cvd['type'] == "copy":
                    continue
                client, fileset = [cvd["client"], cvd["fileset"]]
                [jobs_config[client][fileset].add(pv) for pv in [cvd["pool"], cvd["full backup pool"], cvd["incremental backup pool"]] if pv]
    logger.debug(config_copy_dep)
    return jobs_config, config_copy_dep  # (1)


def hosts():
    """Searches for client resources, parses for address+name and then returns them as dict."""
    files = bacula_config_files()
    _hosts = defaultdict(set)
    for file in files:
        with open (file, "r") as myfile:
            parsed_conf = parse_bacula(myfile)
        if not parsed_conf:
            continue
        for d in parsed_conf:
            if d["resource"].lower() == "client":
                _hosts[d['name']].add(d['address'])
    return _hosts


def host_up():
    """Checks if bacula's file daemon port is open and returns dictionary of available hosts."""
    _hosts = hosts()
    for hk, hv in iteritems(_hosts):
        p2 = Popen([ "/usr/bin/netcat", "-z", "-v", "-w", "2", list(hv)[0], port ], stdout=PIPE, stderr=PIPE, universal_newlines=True)
        out, err = p2.communicate()
        if "succeeded" in err:
            _hosts[hk].add(1)
        else:
            _hosts[hk].add(0)
    return _hosts

# (1) don't sort the dictionaries here yet, because we still need the set() values.
# (2) besides creating jobs_config dictionary, we also create our config_copy_dependency dictionary here.
# (3) continue with next loop if neither in jobdefs nor in jobs config a setting is defined for either pool,client or fileset.

