from securicad import enterprise
import json
import zipfile
import shutil
import os
from attackg import AttackGraph, merge_attack_graphs

temp_inf = 1.7976931348623157e+308

################# your input required


if __name__ == "__main__":
    # securiCAD Enterprise credentials
    username = "XXXX" #################
    password = "XXXX" #################

    # (Optional) Organization of user
    # If you are using the system admin account set org = None
    org = "kth"

    # (Optional) CA certificate of securiCAD Enterprise
    # If you don't want to verify the certificate set cacert = False
    cacert = False

    # securiCAD Enterprise URL
    url = "XXXX"  #################

    # Create an authenticated enterprise client
    client = enterprise.client(
        base_url=url, username=username, password=password, organization=org, cacert=cacert
    )

    # Get the project where the model will be added
    project = client.projects.get_project_by_name("XXXX")  #################
    print("Project pid  -- ", project.pid)

    # Get the model info for the target model from the project
    # models = enterprise.models.Models(client).list_models(project)
    models = enterprise.models.Models(client)
    modelinfo = models.get_model_by_mid(project, "XXXX")  #################
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
    model_file_name = model_path[model_path.rindex('/')+1:model_path.rindex('.')]
    unzip_dir = "scad_dir"
    unzip_dir_path = "{}/{}".format(model_dir_path, unzip_dir)
    with zipfile.ZipFile(model_path, 'r') as zip_ref:
        zip_ref.extractall(unzip_dir_path)
    eom_path = "{}/{}.eom".format(unzip_dir_path, model_file_name)
    print("model unzipped in  -- ", unzip_dir_path)

    # delete the downloaded model file
    os.remove(model_path)
    print("downloaded model deleted")

    # zip the model
    shutil.make_archive(base_name='{}/tempTemp'.format(model_dir_path), format='zip', root_dir=unzip_dir_path)
    zipped_path = '{}/tempTemp.zip'.format(model_dir_path)
    sCAD_path = '{}/tempTemp.sCAD'.format(model_dir_path)
    os.rename(zipped_path, sCAD_path)
    print("model zipped")


    # upload the model
    f1 = open(sCAD_path, "rb")
    modelinfo = models.upload_scad_model(project, "tempTemp.sCAD", f1)
    f1.close()
    print("model uploaded")

    # delete the .sCAD file and model file
    os.remove(sCAD_path)
    # delete all the files in scad_dir
    shutil.rmtree(unzip_dir_path)
    print("model related files deleted")



    # scenario
    scenarios = enterprise.scenarios.Scenarios(client)

    # cleaning old scenarios
    print("scenario cleaning process started ...")
    scen_arios = scenarios.list_scenarios(project)
    for scen_ario in scen_arios:
        scen_ario.delete()
    print("cleaning done")

    # create scenario
    scenario = scenarios.create_scenario(project, modelinfo, "test")

    print("scenario created")

    # create simulation
    simulations = enterprise.simulations.Simulations(client)
    simulation = simulations.create_simulation(scenario)
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

    # get all critical paths
    # cri_path = simulation.get_critical_paths(None)

    attack_paths = []

    # get selected critical paths - where ttc5 is less than infinity
    for risks_i in simres["results"]["risks"]:
        if round(float(risks_i["ttc5"]), 3) == temp_inf:
            continue
        cri_path = simulation.get_critical_paths([risks_i["attackstep_id"]])
        print("critical path fetched")
        ag = AttackGraph(cri_path, risks_i["attackstep_id"])
        print("critical path converted to a graph")
        attack_paths.append(ag)

    # # code for debugging



    graph = merge_attack_graphs(attack_paths)

    crit_metric = 'f'
    graph.find_critical_attack_step(crit_metric)

    graph.find_best_defense()
    #TODO enable the defense in securicad model




