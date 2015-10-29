# Bacula_monitor
Displays most recent successful job for each client's fileset pools on one page and additionally compares
it to your configured jobs to show by markup, whether a backup is missing. Moreover you can configure for
defined pools a timeout value (in days), after that the backup should be marked up as old (yellow).
Your config file (you have to specify the path in functions.py) will be parsed for the configured clients
and thus checked for connectivity on port 9102, to indicate whether your client's bacula service is up or down.
![Alt text](http://i.imgur.com/7p8jMAx.jpg "web-ui")

## Requirements:
python3-Django >= 1.8.4 (opensuse's package name)
netcat
 -or-
pip3 install Django
pip3 install psycopg2

Optionally:
virtualenv


## Installation
The python web framework django is required. I run this web app in a virtualenv with 
apache, but you can also run it without a virtualenv. 
Check the provided apache example config out, which i setup for my virtualenv.

If you decide to use virtualenv. Here's one info link:
virtualenv: 
https://www.jeffknupp.com/blog/2012/02/09/starting-a-django-project-the-right-way/

Another requirement is psycopg2 (python postgresql wrapper).
Install it in the virtualenv or systemwide with `pip3 install psycopg2`


## Configuration
The monitor requires you too outsource your jobdef and jobs files.
specify the path jobdef path and the path where your jobs reside in monitor/functions.py

E.g. in  /etc/bacula/bacula-dir.conf you have:

@/etc/bacula/bacula-dir.d/jobs/jobdefs.conf
@/etc/bacula/bacula-dir.d/jobs/short-term-jobs.conf
@/etc/bacula/bacula-dir.d/jobs/long-term-jobs.conf
@/etc/bacula/bacula-dir.d/jobs/copy-jobs.conf
@/etc/bacula/bacula-dir.d/jobs/misc-jobs.conf

Then in monitor/functions.py add at the top:
jobdefs_path = /etc/bacula/bacula-dir.d/jobs/jobdefs.conf
jobs_path = /etc/bacula/bacula-dir.d/jobs/
client_config = "/etc/bareos/bacula-dir.d/clients.conf"

-> If you change configurations make sure to restart your webserver.

