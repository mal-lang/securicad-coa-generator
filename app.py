from securicad import enterprise
import configparser
import re
import json
import zipfile
import shutil
import os
import xml.etree.ElementTree as ET
import json
import numpy as np
from attackg import AttackGraph, merge_attack_graphs
from securicad.enterprise.tunings import Tunings
import sys
import warnings
import time

temp_inf = 1.7976931348623157e+308
p_test = False

from flask import Flask, request

app = Flask(__name__)

# suppressing HTTPS insecure connection warnings
suppress = True
if suppress and not sys.warnoptions:
    warnings.simplefilter("ignore")

def read_json_file(filename):
    if os.path.isfile(filename):
        with open(filename, 'r') as json_file:
            return json.load(json_file)
    else:
        return {}


def write_json_file(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

DEBUGGING1=True

JSON_FILENAME = "results.json"
final_result = {}



################# your input required

def efficiency(initial, final):
    '''
    initial and final are dictionaries with the same keys, with values being lists of length at least two.

    initial[x][0] = initial ttc5 for the attack step x
    initial[x][1] = initial ttc50 for the attack step x

    final[x][0] = final ttc5 for the attack step x
    final[x][1] = final ttc50 for the attack step x

    NOTE: securiCAD migth return initial ttc5 equal to zero. this is not good for this efficiency metric.
    also, it doesn't make sense for the attack steps that are not initially compromised.
    so, initial 0 values will be changed to 0.001
    '''
    result = 0
    c = 150
    for x in initial:
        initial5 = max(initial[x][0], 0.001)
        initial50 = max(initial[x][1], 0.001)
        final5 = max(final[x][0], 0.001)
        final50 = max(final[x][1], 0.001)
        if DEBUGGING1:
            print("within Efficiency ttc5 {} - ttc50{} - ".format(initial[x][0], initial[x][1]))
        if initial[x][0] != temp_inf:
            # print("Working")
            if initial[x][1] == temp_inf:
                # print("Working again")
                # ttc5_i is finite, ttc50_i is not
                result += np.power(1.05, -initial5) * min(final5 - initial5, c)
            else:
                # ttc5_i is finite, ttc50_i is also finite
                result += np.power(1.05, -initial5) * min(final5 - initial5, c) + np.power(1.05, -initial50) * min(
                    final50 - initial50, c)
    return round(result, 3)

#if __name__ == "__main__":
def connect():
    if os.path.isfile(JSON_FILENAME):
        os.remove(JSON_FILENAME)
    config = configparser.ConfigParser()
    config.read('coa.ini')

    budget_remaining = 85
    print("BUDGET: ", budget_remaining)

    # Create an authenticated enterprise client
    #to get the results with the simid and get the model_id by taking results["model_data"]["mid"] and then model = get_model_by_mid(model_id)

    print("Log in to Enterprise...", end="")
    client = enterprise.client(
        base_url=config["enterprise-client"]["url"],
        username=config["enterprise-client"]["username"],
        password=config["enterprise-client"]["password"],
        organization=config["enterprise-client"]["org"] if config["enterprise-client"]["org"] else None,
        cacert=config["enterprise-client"]["cacert"] if config["enterprise-client"]["cacert"] else False
    )
    print("done")

    # Must "cheat" here and call a raw API to obtain full language meta.
    # The SDK method client.metadata.get_metadata() will not provide everything needed.
    print("Obtaining full language metadata", end=" ")
    lang_meta = client._get("metadata")


    # TODO Remove me! I am fake code to add cost as a JSON dict to SoftwareVulnerability.Remove
    # {first_use: <integer>, subsequent_use: <integer>}
    #svds = lang_meta["assets"]["Identity"]["defenses"]
    #svr = next((d for d in svds if d["name"] == "TwoFactorAuthentication"), False)
    #svr["metaInfo"]["cost"] = [10, 5]
    #svr["metaInfo"]["cost_time"] = [10, 5]

    svds = lang_meta["assets"]["Identity"]["defenses"]
    svr = next((d for d in svds if d["name"] == "Disabled"), False)
    svr["metaInfo"]["cost"] = [15, 10]
    svr["metaInfo"]["cost_time"] = [30, 10]

    svds = lang_meta["assets"]["SoftwareVulnerability"]["defenses"]
    svr = next((d for d in svds if d["name"] == "Remove"), False)
    svr["metaInfo"]["cost"] = [5, 3]
    svr["metaInfo"]["cost_time"] = [10, 5]

    svds = lang_meta["assets"]["Network"]["defenses"]
    svr = next((d for d in svds if d["name"] == "EavesdropDefense"), False)
    svr["metaInfo"]["cost"] = [7, 5]
    svr["metaInfo"]["cost_time"] = [10, 5]

    svds = lang_meta["assets"]["Data"]["defenses"]
    svr = next((d for d in svds if d["name"] == "DataNotPresent"), False)
    svr["metaInfo"]["cost"] = [10, 5]
    svr["metaInfo"]["cost_time"] = [10, 5]

    print("cost update done")


    # Get the project where the model will be added
    #project = client.projects.get_project_by_name("test")  ################# old
    project = client.projects.get_project_by_name("CoA")  #################
    print("Project pid  -- ", project.pid)

    # Get the model info for the target model from the project
    models = enterprise.models.Models(client).list_models(project)
    if p_test:
        for model in models:
         print(model.mid, "  ", model.name)

    models = enterprise.models.Models(client)
    #modelinfo = models.get_model_by_mid(project, "238548676164277")  ################# old
    #modelinfo = models.get_model_by_mid(project, "226155404398940")  #################
    #modelinfo = models.get_model_by_mid(project, "420963146438357") # cost_Model_3
    #modelinfo = models.get_model_by_mid(project, "114362693739575") # type-7
    #modelinfo = models.get_model_by_mid(project, "235847446704635") # imc
    #modelinfo = models.get_model_by_mid(project, "244665522116755")  # examplemodel
    # modelinfo = models.get_model_by_mid(project, "164553780505755")  # simplemodel
    modelinfo = models.get_model_by_mid(project, "245703741252888")  # cost_Model_3v03
    #modelinfo = models.get_model_by_mid(project, "289357738759438")  # honor_model
    #modelinfo = models.get_model_by_mid(project, "194076259054245")  # demoHonor
    # TODO get the model from simulation id

    print("model name  -- ", modelinfo.name)

    # download the model
    datapath = 'data-models'
    if not os.path.exists(datapath):
        os.makedirs(datapath)
    model_path = "data-models/temp.sCAD"
    scad_dump = modelinfo.get_scad()
    print("model downloaded")
    f1 = open(model_path, "wb")
    f1.write(scad_dump)
    f1.close()

    # unzip the model
    model_dir_path = model_path[:model_path.rindex('/')]
    model_file_name = model_path[model_path.rindex('/') + 1:model_path.rindex('.')]
    unzip_dir = "scad_dir"
    unzip_dir_path = "{}/{}".format(model_dir_path, unzip_dir)
    with zipfile.ZipFile(model_path, 'r') as zip_ref:
        zip_ref.extractall(unzip_dir_path)
    eom_path = "{}/{}.eom".format(unzip_dir_path, modelinfo.name)
    print("model unzipped in  -- ", unzip_dir_path)

    # delete the downloaded model file
    os.remove(model_path)
    print("downloaded model deleted")

    # xml parsing
    with open(eom_path, 'rt') as f:
        tree = ET.parse(f)
        root = tree.getroot()


    model_dict_list = []

    for object in root.iter("objects"):
        #print(object)
        model_dict = {}
        model_dict["name"] = object.attrib['name']
        model_dict["metaConcept"] = object.attrib['metaConcept']
        model_dict["exportedId"] = object.attrib['exportedId']
        model_dict["attributesJsonString"] = json.loads(object.attrib['attributesJsonString'])
        model_dict_list.append(model_dict)
        #print(model_dict_list)



    # scenario
    scenarios = enterprise.scenarios.Scenarios(client)

    # cleaning old scenarios
    # TODO Proper positioning required
    print("scenario cleaning process started ...")
    scen_arios = scenarios.list_scenarios(project)
    for scen_ario in scen_arios:
        scen_ario.delete()
    print("cleaning done")

    # create scenario
    scenario = scenarios.create_scenario(project, modelinfo, "test")

    print("scenario created")

    raw_tunings = []

    count = 0
    initial={}
    intermediate={}
    data = read_json_file(JSON_FILENAME)
    if "CoAs" not in data.keys():
        data["CoAs"] = []
    for main_i in range(30):
        print('DATA IS NOW.................-----------______________---------------------____________')
        print(data)
        print('END .................-----------______________---------------------____________')
        if "initialTTC" not in data.keys():
            data["initialTTC"] = {}

        # create simulation
        simulation = client.simulations.create_simulation(scenario,
                                                       name="With tuning",
                                                       raw_tunings=raw_tunings
                                                       )
        print("simulation created")


        # get ttc values
        simres = simulation.get_results()

        with open("Simulation_Result.json", "w") as outfile:
            json.dump(simres, outfile, indent=4)
        ttcs = {}
        #ttcx = {}
        for risks_i in simres["results"]["risks"]:
            #print(risks_i)
            ttcs[risks_i["attackstep_id"]] = [round(float(risks_i["ttc5"]), 3), round(float(risks_i["ttc50"]), 3), round(float(risks_i["ttc95"]), 3)]
            #ttcx[risks_i["attackstep_id"]] = [round(float(risks_i["ttc5"]), 3), round(float(risks_i["ttc50"]), 3)]
            #print(risks_i["ttc5"], risks_i["ttc50"], risks_i["ttc95"])


            if main_i == 0:
                initial_ttcs_json = ttcs[risks_i["attackstep_id"]]
                #results = '"initialTTC" : {},"results" : [\n '.format(ttcs[risks_i["attackstep_id"]],initial_ttcs_json)
                data["initialTTC"][risks_i["attackstep_id"]] = initial_ttcs_json
                # results = '"initialTTC values for": \n \t {}: {} \n'.format(risks_i["attackstep_id"], initial_ttcs_json)
                # with open('newTestsResults.txt', 'a') as f:
                #     f.write(results)
                #print("TTC values for ", risks_i["attackstep_id"], "is", ttcs[risks_i["attackstep_id"]])
            else:
                initial_ttcs_json = ttcs[risks_i["attackstep_id"]]
                # results = '"coaTTC values for": \n \t {}: {} \n'.format(risks_i["attackstep_id"], initial_ttcs_json)
                
                coa_index = len(data["CoAs"]) - 1
                if "coaTTC" not in data["CoAs"][coa_index].keys():
                    data["CoAs"][coa_index]["coaTTC"] = {}
                data["CoAs"][coa_index]["coaTTC"][risks_i["attackstep_id"]] = initial_ttcs_json
                data["CoAs"][coa_index]["report_url"] = simres["report_url"]

                # with open('newTestsResults.txt', 'a') as f:
                #     f.write(results)
                #print("TTC values for ", risks_i["attackstep_id"], "is", ttcs[risks_i["attackstep_id"]])

            print("TTC values for ", risks_i["attackstep_id"], "is", ttcs[risks_i["attackstep_id"]])
            write_json_file(JSON_FILENAME,data)
        steps_of_interest = ["{}".format(risks_i["attackstep_id"]) for risks_i in simres["results"]["risks"]]
        print("Steps of interest are: ", steps_of_interest)

        '''if main_i==0:
            initial=ttcx
        else:
            intemediate=ttcx
            eff=efficiency(initial, intermediate)'''
        #print(risks_i)

        # get all critical paths
        # cri_path = simulation.get_critical_paths(None)


        #if count>0:
            #coa_efficiency = efficiency(real_initial_ttcs, intermediate_ttcs)
        attack_paths = []

        # get selected critical paths - where ttc5 is less than infinity
        for risks_i in simres["results"]["risks"]:
            if round(float(risks_i["ttc5"]), 3) == temp_inf:
                continue
            cri_path = simulation.get_critical_paths([risks_i["attackstep_id"]])
            print("critical path fetched")
            with open("cp.json", "w") as outfile:
                json.dump(cri_path, outfile)
            ag = AttackGraph(cri_path, risks_i["attackstep_id"], lang_meta)
            print("critical path converted to a graph")
            attack_paths.append(ag)

        if len(attack_paths) == 0:
            return

        # code for debugging

        graph = merge_attack_graphs(attack_paths)

        crit_metric = ['o', 'f']
        for i in range(len(crit_metric)):
            graph.find_critical_attack_step(crit_metric[i])

        # try:
        #try:
        write_json_file(JSON_FILENAME,data)
        best_def_info, budget_remaining = graph.find_best_defense(lang_meta, model_dict_list, budget_remaining)
        data = read_json_file(JSON_FILENAME)
        if p_test:
            print(best_def_info)
        print("BUDGET: ", budget_remaining)
       #except Exception as e:
       #    # write_json_file(JSON_FILENAME,data)
       #    print("EXCEPTION:")
       #    print(e)
       #    print("No suitable defense available")
       #    exit()

        print("MODEL DICT LIST")
        #print(model_dict_list) #########################################################
        print("END MODEL DICT LIST")

        #TODO enable the defense in securicad model

        raw_tunings.append(
            {
                "type": "probability",
                "op": "apply",
                "filter": {"object_name": best_def_info["name"], "defense": best_def_info["attackstep"], "tags": {}},
                "probability": 1.0
            }
        )
        count=count+1
        #print("Count ", count)



@app.route('/', methods=["POST"])
def hello():
    if request.is_json:
        request_data = request.get_json()
        print("JSON Simulation ID : {}".format(request_data['simulationId']))
    else:
        req = request.data
        print("request.data : {}".format(request.data))
        request_data = json.loads(req.decode('ascii'))
        print("Non JSON Simulation ID : {}".format(request_data['simulationId']))

    #r = '{'
    #with open('results.json', 'w') as f:
        #f.write(r)

    connect()

    #r =  ']}'
    #with open('results.json', 'a') as f:
    #    f.write(r)
    print("hello")
    content = read_json_file(JSON_FILENAME)

    R = json.dumps(content)
    print(R)
    #with open("results.json", "r") as fin:
    #    content = json.load(fin)
    #with open("stringResults.json", "w") as fout:
    #    json.dump(content, fout, indent=1)
     #   R = json.dumps(content)


    # convert into JSON:
    #y = json.dumps(x)
    return R
