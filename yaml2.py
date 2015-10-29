import yaml
from voluptuous import Schema, Required, All, Length, Range, MultipleInvalid

with open("example.yaml", 'r') as stream:
    yaml_parsed = yaml.load(stream)
schema = Schema({
    Required('bacula_config_path'): str,
    Required('port'): int,
    'timeouts': Schema({int: [str]}) # if not timeouts set, use default value
})
try:
    schema(yaml_parsed)
    print(yaml_parsed)
except MultipleInvalid as e:
    exc = e
    print(e)
#print(yaml_parsed["timeouts"])

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(BASE_DIR)
