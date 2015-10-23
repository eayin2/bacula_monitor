Configuration
The monitor requires you too outsource your jobdef and jobs files.
specify the path jobdef path and the path where your jobs reside in monitor/functions.py

E.g. in  /etc/bareos/bareos-dir.conf you have:

@/etc/bareos/bareos-dir.d/jobs/jobdefs.conf
@/etc/bareos/bareos-dir.d/jobs/short-term-jobs.conf
@/etc/bareos/bareos-dir.d/jobs/long-term-jobs.conf
@/etc/bareos/bareos-dir.d/jobs/copy-jobs.conf
@/etc/bareos/bareos-dir.d/jobs/misc-jobs.conf

Then in monitor/functions.py add at the top:
jobdefs_path = /etc/bareos/bareos-dir.d/jobs/jobdefs.conf
jobs_path = /etc/bareos/bareos-dir.d/jobs/

