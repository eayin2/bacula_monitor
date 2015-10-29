import json
from jsonschema import validate
confPath = "bacula_monitor.conf"
def json_config():
    schema = json.load(open("schema.json"))
    jsonConfig = json.load(open(confPath))
    if validate(jsonConfig, schema) is None:
        print("jsconConfig valid.")
    else:
        print("jsconConfig not valid.")
    configKeyMainList = list()
    for keyMain in jsonConfig:
        if keyMain == "remote" and mode == "client":
            continue
        configKeyMainList.append(keyMain)
    return jsonConfig

print(json_config())
