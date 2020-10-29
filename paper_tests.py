from securicad import Session, User
from securicad.coagen import CoAGenerator, overline_pre, efficiency
from securicad.model import Model
from securicad.attackg import AttackGraph, merge_attack_graphs
import sys
import warnings
import time
import numpy as np
import networkx as nx

# suppressing HTTPS insecure connection warnings
suppress = True
if suppress and not sys.warnoptions:
    warnings.simplefilter("ignore")

def batchTestUkraine(N=20, iters=5, doneSoFar=1, defs_per_iter=4):
    '''
    This function will run the 'testUkraineModel' function for every integer in the range (doneSoFar, N].
    '''
    # initial ttcs grabbed from some simulation. used for computing efficiency scores of results, so that they are computed wrt the same initial ttcs.
    initial_ttcs = {'74.Compromise': [0.001, 21.556, 1.7976931348623157e+308], '59.Compromise': [0.001, 21.556, 1.7976931348623157e+308], '3.Compromise': [0.0, 0.0, 1.7976931348623157e+308]}
    test_index = doneSoFar
    while test_index < N:
        # tries&excepts because of internet connection issues/securiCAD's sudden deaths
        try:
            testUkraineModel(test_index, iters, initial_ttcs, defs_per_iter)
            test_index += 1
        except:
            time.sleep(5*66)
    return

def testUkraineModel(test_index, iters, initial_ttcs, defs_per_iter, number_of_targets = 3):
    '''
    Run CoA Generator on the Ukraine model. One CoA will be generated for each of the following criticality metrics: frequency,
    weighted outdegree, combination (frequency, weighted outdegree) of the two.

    Pass 'iters' (limit on the number of simulations) and 'defs_per_iter' to the generator.
    Use 'initial_ttcs' (given in 'batchTestUkraine') to compute efficiency of the result.

    Result will be saved in 'newTestsResults_Ukraine_*.txt', with the value of 'test_index' in the place of the asterisk.
    Format of the file:
        f
        <final TTC values for first target>
        ...
        <final TTC values for last target>
        <efficiency score>
        <CoA (= list of defense steps)>
        <runtime>
        iterations: <number of executed iterations of the main loop of the algorithm>

        o
        <final TTC values for first target>
        ...
        <final TTC values for last target>
        <efficiency score>
        <CoA (= list of defense steps)>
        <runtime>
        iterations: <number of executed iterations of the main loop of the algorithm>

        fo
        <final TTC values for first target>
        ...
        <final TTC values for last target>
        <efficiency score>
        <CoA (= list of defense steps)>
        <runtime>
        iterations: <number of executed iterations of the main loop of the algorithm>
    '''
    resultsSummary = ''
    TEST_USER = User(name='widel', password='j6r2kG9B7Tx#pm45sMTTi',
                      organization='SOCCRATES', role='system admin')
    TEST_SESSION = Session(ip_address='35.228.217.8', user=TEST_USER)
    TEST_PROJECT_ID = "159713165450162"

    # prepare
    delete_all(TEST_SESSION, TEST_PROJECT_ID)

    # 1. setup
    model_id = "119627366873844"
    # target assets: RTU control, SCADA host, SCADA network
    if number_of_targets == 3:
        target_objects_ids = ("-1918147270271938948", "-4248293001840213491", "2256227903192124367")

    # paths to inputs
    costs_path = 'paper_tests_ukraine\\ukraine_costs.json'
    times_path = 'paper_tests_ukraine\\ukraine_times.json'
    monetary_budgets_path = 'paper_tests_ukraine\\ukraine_budgets_monetary.json'
    time_budgets_path = 'paper_tests_ukraine\\ukraine_budgets_time.json'
    prerequisites_path = 'paper_tests_ukraine\\ukraine_pre.json'
    exclusivity_path = 'paper_tests_ukraine\\ukraine_excl.json'

    for metric in ['f', 'o', 'fo']:
        generator = CoAGenerator(TEST_SESSION, costs_path, times_path, monetary_budgets_path,
                                time_budgets_path, prerequisites_path, exclusivity_path)
        tic = time.time()
        result = generator.generate_coas(project_id=TEST_PROJECT_ID, model_id=model_id,
                                         target_objects_ids=target_objects_ids,
                                         crit_metrics=[metric], iterations_number_limit=iters, defs_per_iteration=defs_per_iter, test_for_paper=True)
        # result = ([(CoA, Eff, FinalTTCs)], InitTTCs, Iterations)
        toc = time.time()
        runtime = toc-tic

        # recompute efficiency
        coaFinalTTCs = result[0][0][2]
        coa_efficiency = efficiency(initial_ttcs, coaFinalTTCs)
        actual_coa = result[0][0][0]

        # result
        metric_res = '{}\n'.format(metric)
        for step in initial_ttcs:
            metric_res +='{}: {}, {}\n'.format(step, coaFinalTTCs[step][0], coaFinalTTCs[step][1])
        metric_res += '{}\n'.format(coa_efficiency)
        metric_res += '{}\n'.format(actual_coa.hasse.nodes)
        metric_res += '{}\n'.format(runtime)
        #print(len(result))
        #print(result)
        metric_res += 'iterations: {}\n\n'.format(result[2])

        resultsSummary += metric_res

    with open('newTestsResults_Ukraine_{}.txt'.format(test_index), 'w') as f:
        f.write(resultsSummary)

    return


def testSegrid(test_index = 0, iters = 1, defs_per_iter=1):
    '''
    Run CoA Generator on the SEGRID model. One CoA will be generated for each of the following criticality metrics: frequency,
    weighted outdegree, combination (frequency, weighted outdegree) of the two.

    Pass 'iters' (limit on the number of simulations) and 'defs_per_iter' to the generator.

    Result will be saved in 'TestsResults_SEGRID_*.txt', with the value of 'test_index' in the place of the asterisk.
    Format of the file:
        f
        <final TTC values for first target>
        ...
        <final TTC values for last target>
        <efficiency score>
        <runtime>
        iterations: <number of executed iterations of the main loop of the algorithm>

        o
        <final TTC values for first target>
        ...
        <final TTC values for last target>
        <efficiency score>
        <runtime>
        iterations: <number of executed iterations of the main loop of the algorithm>

        fo
        <final TTC values for first target>
        ...
        <final TTC values for last target>
        <efficiency score>
        <runtime>
        iterations: <number of executed iterations of the main loop of the algorithm>
    '''
    resultsSummary = ''
    TEST_USER = User(name='widel', password='j6r2kG9B7Tx#pm45sMTTi',
                      organization='SOCCRATES', role='system admin')
    #TEST_SESSION = Session(ip_address='35.228.217.8', user=TEST_USER)
    TEST_PROJECT_ID = "159713165450162"

    # prepare
    #delete_all(TEST_SESSION, TEST_PROJECT_ID)

    # 1. setup
    model_id = "269462549617583"
    # target assets: DSO_OfficeComputer, DSO_Scada_ScadaServer, DSO_SCADA_DataEngineeringHMI
    target_objects_ids = ("-7459328391749153334", "-2339554128504993591", "-8057210135376477891")

    #
    initial_ttcs = {'102.Compromise': [10.0, 41.0, 1.7976931348623157e+308],#DSO_OfficeComputer
                    '271.Compromise': [5.0, 27.0, 1.7976931348623157e+308],#DSO_Scada_ScadaServer
                    '277.Compromise': [20.0, 48.0, 1.7976931348623157e+308]}#DSO_SCADA_DataEngineeringHMI

    for metric in ['f', 'o', 'fo']:
        # will establish connection for every metric to avoid token expiration?
        TEST_SESSION = Session(ip_address='35.228.217.8', user=TEST_USER)
        delete_all(TEST_SESSION, TEST_PROJECT_ID)
        generator = CoAGenerator(TEST_SESSION)
        tic = time.time()
        result = generator.generate_coas(project_id=TEST_PROJECT_ID, model_id=model_id,
                                         target_objects_ids=target_objects_ids,
                                         crit_metrics=[metric], iterations_number_limit=iters, time_limit=3600, defs_per_iteration=defs_per_iter, test_for_paper=True)

        toc = time.time()
        runtime = toc-tic

        # recompute efficiency
        coaFinalTTCs = result[0][0][2]
        coa_efficiency = efficiency(initial_ttcs, coaFinalTTCs)

        # result
        metric_res = '{}\n'.format(metric)
        for step in initial_ttcs:
            metric_res +='{}: {}, {}\n'.format(step, coaFinalTTCs[step][0], coaFinalTTCs[step][1])
        metric_res += '{}\n'.format(coa_efficiency)
        metric_res += '{}\n'.format(runtime)
        #print(len(result))
        #print(result)
        metric_res += 'iterations: {}\n\n'.format(result[2])

        resultsSummary += metric_res

    with open('TestsResults_SEGRID_{}.txt'.format(test_index), 'w') as f:
        f.write(resultsSummary)
    return


# def test_runtime_wrt_targetsteps(test_indices=[0], number_of_targets=4):
#     for test_index in test_indices:
#         test_U5f_wrt_targets(test_index, number_of_targets)
#     return


def test_U5f_wrt_targets(test_index=0, number_of_targets = 8):
    '''
    Run CoA Generator on the Ukraine model, using 'frequency' criticality metric, with 5 iterations and at least 4 defenses
    added per iteration (called 'U5f' in the paper), for the given number of target objects.

    number_of_targets in [2,4,6,8]

    Result will be saved in 'exp_U5f_*targets/test_*.txt', with the value of 'number_of_targets' in the place of the first asterisk,
    and the value of 'test_index' in the place of the second asterisk.
    Format of the file:

        <runtime>
        <efficiency>
        <final TTC values for first target>
            ...
        <final TTC values for last target>
        <CoA (= list of defense steps)>
    '''
    # RTU control, SCADA host, SCADA network, Windows 7 workstation, VPN controller, VPN client, RTU host, SCADA service
    targets = ["-1918147270271938948", "-4248293001840213491", "2256227903192124367", "-8424983804150529133", "-3202611913357899626", "-6408195127799824249", "8319923424196972390", "-8690788767972637605"]
    TEST_USER = User(name='widel', password='j6r2kG9B7Tx#pm45sMTTi',
                      organization='SOCCRATES', role='system admin')
    TEST_SESSION = Session(ip_address='35.228.217.8', user=TEST_USER)
    TEST_PROJECT_ID = "159713165450162"

    # prepare
    delete_all(TEST_SESSION, TEST_PROJECT_ID)

    # 1. setup
    model_id = "231141588838243"

    target_objects_ids = tuple(targets[:number_of_targets])

    # paths to inputs
    costs_path = 'paper_tests_ukraine\\ukraine_costs.json'
    times_path = 'paper_tests_ukraine\\ukraine_times.json'
    monetary_budgets_path = 'paper_tests_ukraine\\ukraine_budgets_monetary.json'
    time_budgets_path = 'paper_tests_ukraine\\ukraine_budgets_time.json'
    prerequisites_path = 'paper_tests_ukraine\\ukraine_pre.json'
    exclusivity_path = 'paper_tests_ukraine\\ukraine_excl.json'

    # U5f
    metric = 'f'
    iters = 5
    defs_per_iter = 4

    # run
    generator = CoAGenerator(TEST_SESSION, costs_path, times_path, monetary_budgets_path,
                                time_budgets_path, prerequisites_path, exclusivity_path, test_for_paper=True)
    tic = time.time()
    result = generator.generate_coas(project_id=TEST_PROJECT_ID, model_id=model_id,
                                         target_objects_ids=target_objects_ids,
                                         crit_metrics=[metric], iterations_number_limit=iters, defs_per_iteration=defs_per_iter)
    toc = time.time()
    runtime = toc-tic

    actual_coa = result[0][0][0]
    coaFinalTTCs = result[0][0][2]

    # recompute efficiency
    #
    initial_ttcs = {'74.Compromise': [0.0, 0.0, 0.0], # RTU control
                    '59.Compromise': [0.0, 0.0, 0.0]} # SCADA host
    if number_of_targets >= 4:
        initial_ttcs['3.Compromise'] = [0.0, 0.0, 0.0]
        initial_ttcs['20.Compromise'] = [0.0, 0.0, 0.0]
    if number_of_targets >= 6:
        initial_ttcs['29.Compromise'] = [0.0, 3.0, 23.0]
        initial_ttcs['27.Compromise'] = [0.0, 0.0, 0.0]
    if number_of_targets == 8:
        initial_ttcs['73.Compromise'] = [0.0, 0.0, 0.0]
        initial_ttcs['54.Compromise'] = [0.0, 0.0, 0.0]

    coa_efficiency = efficiency(initial_ttcs, coaFinalTTCs)

    # create results summary
    res_path = 'exp_U5f_{}targets\\test_{}.txt'.format(number_of_targets, test_index)
    res = '{}\n'.format(runtime)
    res += '{}\n'.format(coa_efficiency)
    for step in initial_ttcs:
        res +='{}: {}, {}\n'.format(step, coaFinalTTCs[step][0], coaFinalTTCs[step][1])
    res += '{}\n'.format(actual_coa.hasse.nodes)

    with open(res_path, 'w') as f:
        f.write(res)

    return

def tesst():
    '''
    Quick look at efficiency scores assigned to different changes in TTCs. Just to see if the scores feel right.
    '''
    initial = [0.01,1, 10, 20, 30, 100, 100, np.inf]
    final = [10, 10,30, 30, 70, 140, np.inf, np.inf]
    for j in range(len(initial)):
        d = final[j] - initial[j]
        score = np.power(1.05, -initial[j]) * d
        print(initial[j], final[j], score)
    for item in initial:
        print(np.power(1.05, item))
    return

def delete_all(TEST_SESSION, project_id):
    '''
    Deletes every model from the project having id 'project_id', other than 5 models specified below.
    Deletes all 'scenarios'.
    '''
    tids = TEST_SESSION.get_scenarios_tids(project_id=project_id)
    for tid in tids:
        TEST_SESSION.delete_scenario_from_project(scenario_id=tid, project_id=project_id)

    mids = TEST_SESSION.get_models_mids(project_id=project_id)
    for mid in mids:
        if mid not in ["119627366873844", "269462549617583", "231141588838243", "547232914798682", "498789380844589"]:
            TEST_SESSION.delete_model_from_project(project_id=project_id, model_id=mid)
    return

def delete_stuff():
    '''
    CAREFUL!
    Deletes every model from the 'newlife' project in securiCAD, other than 5 models specified above.
    Deletes all 'scenarios'.
    '''
    TEST_USER = User(name='widel', password='j6r2kG9B7Tx#pm45sMTTi',
                      organization='SOCCRATES', role='system admin')
    TEST_PROJECT_ID = "159713165450162"
    TEST_SESSION = Session(ip_address='35.228.217.8', user=TEST_USER)
    delete_all(TEST_SESSION, TEST_PROJECT_ID)
    return


def talk():
    '''
    Quick code for ilustrating the CoA Generator. Creates .graphml files storing some attack paths, and an attack
    graph arising from merging the attack paths. The files can be used for visualisation, e.g., using Cytoscape.
    '''
    time_limit = 300

    # ip_address, username, password => session
    user = User(name='widel', password='j6r2kG9B7Tx#pm45sMTTi',
                      organization='SOCCRATES', role='system admin')
    session = Session(ip_address='35.228.217.8', user=user)

    project_id = "159713165450162"
    model_id = "547232914798682" # base
    model_id = "498789380844589" # with AccessControl.104.AD SSO Admin.Enabled

    # targets: RTU control, SCADA host
    target_objects_ids = ["-1918147270271938948", "-4248293001840213491"]

    #generator = CoAGenerator(session)

    eom_file_path = session.download_and_unzip_model(project_id, model_id, outpath=None, feedback = False)
    eom_dir_path = eom_file_path[:eom_file_path.rindex('\\')]
    model = Model(eom_file_path)
    steps_of_interest = ["{}.Compromise".format(model.get_exportedId_from_id(object_id)) for object_id in
                         target_objects_ids]

    # run simulations
    simid, tid = session.run_simulation(project_id=project_id, model_id=model_id, time_limit=time_limit)

    # fetch attack paths and merge them into a single attack graph
    attack_paths = [AttackGraph(session.get_attack_path_from_simulation(simulation_id=simid,
                                                                                          attack_step=step_of_interest,
                                                                                          time_limit=time_limit)) for step_of_interest in steps_of_interest]
    graph = merge_attack_graphs(attack_paths)

    graphs_to_draw = {'FW_attack_paths_RTU_control': attack_paths[0], 'FW_attack_paths_SCADA_host': attack_paths[1], 'FW_whole_graph': graph}

    for item in graphs_to_draw:
        G = graphs_to_draw[item]
        file_name = 'TALK\\' + item + '.graphml'
        for node in G.nodes:
            if G.nodes[node]["isDefense"]:
                G.nodes[node]["color"] = "green"
                G.nodes[node]["outdegree"] = "NA"
            else:
                G.nodes[node]["color"] = "red"
                G.nodes[node]["outdegree"] = sum([G.nodes[child]["frequency"] for child in G.successors(node)])

        G.set_criticality_scores_of_counterable_attack_steps(metrics = 'o', only_counterable = False)

        for node in G.nodes:
            if G.nodes[node]["isDefense"]:
                countered_by_the_node = set([child for child in G.successors(node)])
                G.nodes[node]["crit_score"] = max([G.nodes[node]["crit_score"] for node in countered_by_the_node])

        nx.write_graphml(G, file_name)

    return


if __name__ == '__main__':
    talk()
    sys.exit()
    #N = 20
    #iters = 5
    #defs_per_iter = 4
    delete_stuff()
    #batchTestUkraine(26, iters=iters, doneSoFar=25, defs_per_iter = defs_per_iter)
    sys.exit()

    #cur_ind = 17#18#19
    #for cur_ind in [19]:
    #    testSegrid(test_index=cur_ind, iters=5, defs_per_iter= 4)

    batchTestUkraine(N=16, doneSoFar=14)
    sys.exit()

    for t in [6]:
        # REMEMBER ABOUT GRAPH SIZES
        #for indices in [[3*i, 3*i+1, 3*i+2] for i in range(6)]:
        for indices in [[18, 19]]:#[i for i in range(14,20)]]:
            start = time.time()
            test_runtime_wrt_targetsteps(test_indices=indices, number_of_targets=t)
            end = time.time()
            mins = (end-start)//60
            secs = (end-start)%60
            print('DONE. REMEMBER ABOUT GRAPH SIZES. t={}, took {} min. and {} secs.'.format(t,mins,secs))
            #sys.exit()
            # after each exit, restart the VM and increase the starting value of range() by one