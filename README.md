# Bacula_monitor
Displays most recent successful job for each client's fileset pools on one page and additionally compares
it to your configured jobs to show by markup, whether a backup is missing. Moreover you can configure for
defined pools a timeout value (in days), after that the backup should be marked up as old (yellow).
Your config file (you have to specify the path in functions.py) will be parsed for the configured clients
and thus checked for connectivity on port 9102, to indicate whether your client's bacula service is up or down.
<br />
![Alt text](http://i.imgur.com/7p8jMAx.jpg "web-ui")

## Requirements:
Django >= 1.8.4 <br />
netcat <br />
psycopg2 <br />
PyYAML <br />
voluptuous <br />
nginx (with uwsgi) or apache2 (with mod_wsgi) <br />
Optionally (recommended): <br />
virtualenv <br />


## Installation
The python web framework django is required. I run this web app in a virtualenv with 
apache, but you can also run it without a virtualenv. 
Check the provided apache example config out, which i setup for my virtualenv. <br />
If you decide to use virtualenv. Here's one info link:<br />
https://www.jeffknupp.com/blog/2012/02/09/starting-a-django-project-the-right-way/ <br />
See the requirements above, that have to be installed for bacula_monitor to work.

mkdir -p /var/log/django/
chown -R wwwrun /var/log/django/
(where wwwrun is the user who runs wsgi (depending on your distro webserver package/setup it might be wwwrun, http or another user))

## Configuration
See bm.conf example config file for available settings.
Make sure to restart your webserver after editing the config file.

