# used earlier in functions.py
def jobdefs_values(jobdef_name, value_list):
    """ parses jobdefs.conf and returns values for given keys packed in a dictionary. """
    with open (bacula_config_path, "r") as myfile:
        jobdefs_parsed = parse_bacula(myfile)
    value_dict = defaultdict()
    for dict in jobdefs_parsed:
        dict = {k.lower():v for k,v in dict.items()}
        if dict["name"] == jobdef_name and dict["resource"] == "jobdefs":
            for value in value_list:
                try:
                    value_dict[value] = dict[value]
                except Exception as err:
                    print(err)
                    print("jobdefs has dict[%s] neither." % value)
    return value_dict

