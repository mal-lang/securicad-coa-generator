from securicad.session import Session
from securicad.user import User
from securicad.coagen import CoAGenerator, overline_pre, efficiency
from securicad.model import Model
from securicad.attackg import AttackGraph, merge_attack_graphs
import sys
import warnings
import time
import numpy as np
import networkx as nx


def testUkraineModel():
    '''
    100 samples per simulation
    '''
    TEST_USER = User(name='widel', password='j6r2kG9B7Tx#pm45sMTTi',
                      organization='SOCCRATES', role='system admin')
    TEST_SESSION = Session(ip_address='35.228.217.8', user=TEST_USER)
    TEST_PROJECT_ID = "159713165450162"

    # 1. setup
    model_id = "119627366873844"
    # target assets: RTU control, SCADA host, SCADA network. these are securiCAD's objects' ids.
    # seems sufficient to use exportedIds instead because to get attack paths from simulations, you need
    # to provide target attack steps in the form "exportedId.step_name" (in practice "exportedID.Compromise").
    target_objects_ids = ("-1918147270271938948", "-4248293001840213491", "2256227903192124367")

    # paths to inputs
    costs_path = 'paper_tests_ukraine\\ukraine_costs.json'
    times_path = 'paper_tests_ukraine\\ukraine_times.json'
    monetary_budgets_path = 'paper_tests_ukraine\\ukraine_budgets_monetary.json'
    time_budgets_path = 'paper_tests_ukraine\\ukraine_budgets_time.json'
    prerequisites_path = 'paper_tests_ukraine\\ukraine_pre.json'
    exclusivity_path = 'paper_tests_ukraine\\ukraine_excl.json'

    metric = 'o' # criticality metric used is the weighted outdegree
    iters = 5 # 5 iterations
    defs_per_iter = 3 # at least 3 defenses added per iteration (if possible)

    # 2. generation

    generator = CoAGenerator(TEST_SESSION, costs_path, times_path, monetary_budgets_path,
                                time_budgets_path, prerequisites_path, exclusivity_path)


    #criticality_metrics = ['f', 'o', 'of']

    result = generator.generate_coas(project_id=TEST_PROJECT_ID, model_id=model_id,
                                     target_objects_ids=target_objects_ids,
                                     crit_metrics=[metric], iterations_number_limit=iters, defs_per_iteration=defs_per_iter)

    for item in result:
        print(item)

    return


if __name__ == '__main__':
    testUkraineModel()