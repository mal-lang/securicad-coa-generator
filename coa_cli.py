from securicad import enterprise
import configparser
import re
import json
import zipfile
import shutil
import os
import xml.etree.ElementTree as ET
import json
from attackg import AttackGraph, merge_attack_graphs

temp_inf = 1.7976931348623157e+308
p_test = False

################# your input required


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('coa.ini')

    budget_remaining = 50
    print("BUDGET: ", budget_remaining)

    # Create an authenticated enterprise client
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
    print("Obtaining full language metadata", end="")
    lang_meta = client._get("metadata")


    # TODO Remove me! I am fake code to add cost as a JSON dict to SoftwareVulnerability.Remove
    # {first_use: <integer>, subsequent_use: <integer>}
    svds = lang_meta["assets"]["Identity"]["defenses"]
    svr = next((d for d in svds if d["name"] == "TwoFactorAuthentication"), False)
    svr["metaInfo"]["cost"] = '{"first_use":10, "subsequent_use":100}'
    print("cost update done")
    svds = lang_meta["assets"]["Identity"]["defenses"]
    svr = next((d for d in svds if d["name"] == "Disabled"), False)
    svr["metaInfo"]["cost"] = '{"first_use":10, "subsequent_use":100}'
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
    modelinfo = models.get_model_by_mid(project, "420963146438357") # cost_Model_3
    #modelinfo = models.get_model_by_mid(project, "114362693739575") # type-7
    #modelinfo = models.get_model_by_mid(project, "243886861364858")
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

    for main_i in range(3):

        # create simulation
        simulation = client.simulations.create_simulation(scenario,
                                                       name="With tuning",
                                                       raw_tunings=raw_tunings
                                                       )
        print("simulation created")


        # get ttc values
        simres = simulation.get_results()
        with open("Simulation_Result.json", "w") as outfile:
            json.dump(simres, outfile)
        ttcs = {}
        for risks_i in simres["results"]["risks"]:
            ttcs[risks_i["attackstep_id"]] = [round(float(risks_i["ttc5"]), 3), round(float(risks_i["ttc50"]), 3), round(float(risks_i["ttc95"]), 3)]
            print("TTC values for ", risks_i["attackstep_id"], "is", ttcs[risks_i["attackstep_id"]])
        steps_of_interest = ["{}".format(risks_i["attackstep_id"]) for risks_i in simres["results"]["risks"]]
        print("Steps of interest are: ", steps_of_interest)

        # get all critical paths
        # cri_path = simulation.get_critical_paths(None)

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
            exit()

        # code for debugging

        graph = merge_attack_graphs(attack_paths)

        crit_metric = 'f'
        graph.find_critical_attack_step(crit_metric)

        try:
            best_def_info, budget_remaining = graph.find_best_defense(lang_meta, model_dict_list, budget_remaining)
            if p_test:
                print(best_def_info)
            print("BUDGET: ", budget_remaining)
        except:
            print("No suitable defense available")
            exit()


        #TODO enable the defense in securicad model
        raw_tunings.append(
            {
                "type": "probability",
                "op": "apply",
                "filter": {"object_name": best_def_info["name"], "defense": best_def_info["attackstep"], "tags": {}},
                "probability": 1.0
            }
        )





