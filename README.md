# Bacula_monitor
Displays most recent successful job for each client's fileset pools on one page and additionally compares
it to your configured jobs to show by markup, whether a backup is missing. Moreover you can configure for
defined pools a timeout value (in days), after that the backup should be marked up as old (yellow).
Your config file (you have to specify the path in functions.py) will be parsed for the configured clients
and thus checked for connectivity on port 9102, to indicate whether your client's bacula service is up or down.
![Alt text](http://i.imgur.com/7p8jMAx.jpg "web-ui")

## Requirements:
Django >= 1.8.4
netcat
psycopg2
PyYAML
voluptuous

Optionally (recommended):
virtualenv


## Installation
The python web framework django is required. I run this web app in a virtualenv with 
apache, but you can also run it without a virtualenv. 
Check the provided apache example config out, which i setup for my virtualenv.

If you decide to use virtualenv. Here's one info link:
virtualenv: 
https://www.jeffknupp.com/blog/2012/02/09/starting-a-django-project-the-right-way/

See the requirements above, that have to be installed for bacula_monitor to work.


## Configuration
See bm.conf example config file for available settings.
Make sure to restart your webserver after editing the config file.

