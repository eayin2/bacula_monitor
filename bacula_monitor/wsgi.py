"""
WSGI config for bacula_monitor project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/howto/deployment/wsgi/
"""
import os
from monitor.functions import validate_yaml
yaml_parsed = validate_yaml()
try:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ENV_PATH = str(yaml_parsed["virtualenv"])
    import sys
    sys.path.append(BASE_DIR)
    # add the virtualenv site-packages path to the sys.path
    sys.path.append(ENV_PATH)
except:
    pass
from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bacula_monitor.settings")
application = get_wsgi_application()
