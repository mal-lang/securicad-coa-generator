from securicad.model import Model
from securicad.coa import CoA
from securicad.attackg import AttackGraph, merge_attack_graphs
import json
import numpy as np
import copy
import sys
import time

DEBUGGING = True

class CoAGenerator():

    def __init__(self, session, costs_path = '', times_path = '', monetary_budgets_path = '', time_budgets_path = '', prerequisites_path = '', exclusivity_path = ''):
        '''
        TODO: in the future needs to be adapted to get costs etc. as arguments from the Orchestrator (and not local files).
        IMPORTANT: in what is described below, "defense_step" is of the form "class.eid.object_name.step_name"
        see comments in AttackGraph._get_params_from_json to see how this format is constructed from attack paths
        fetched from securiCAD.

        === Expected format of .json files containing cost specifications (files under 'costs_path' and 'times_path'):

        {
            "1": {
                "defense_step1": float_value,
                "defense_step2": {
                    "default": float_value,
                    "same_type_dependency": {
                        "int": float_value,
                        ...
                        "int": float_value,
                    },
                    "different_type_dependency": {
                        "defense_step": "+float",
                        "defense_step": "-float",
                        "defense_step": "*float"
                    }
                }
            }
            "2": ...
        }

        Interpretation:

        - The first cost of implementation of "defense_step1" is constant, doesn't depend on implementation of other steps,
        and is equal to float_value1.
        - By default, the first cost of implementation of "defense_step2" is equal to float_value2. However, the cost depends
        on implementation of other steps.
        If "defense_step2" is implemented along exactly one other step of the same type (e.g., if "defense_step2" = "host1.patch",
        then by 'the same type' we mean 'patch' defense steps applied to instances of 'host' asset), then its cost is 12.
        If "defense_step2" is implemented along two or more other steps of the same type (say, "host2.patch" and "host3.patch
        with "defense_step2" = "host1.patch"), then its cost is 10.
        Once steps of the same type are analyzed, the base cost of "defense_step2" is established. It is later modified depending
        on defense steps of other types: if "defense_step3" is to be implemented along "defense_step2", then the cost of "defense_step2"
        is increased by 10, etc.

        Note: haven't thought it through, the final cost will depend on the order in which the operations coming from dependencies
        on steps of other types are performed. Well, this is a prototype. Should be taken care of in the final version.

        Note: monetary and time-like cost specifications should be stored in separate files.


        === Expected format of .json files containing budget specifications (files under 'monetary_budgets_path' and 'time_budgets_path'):

        {
            "1": float,
            "2": float,
            ...
            "n": float
        }

        === Expected format of .json files containing prerequisites and exclusivity specifications (files under 'prerequisites_path' and 'exclusivity_path'):

        {
            "defense_step": ["def_step2", "def_step3"],
            "def_step2": ["def_step5"]
        }
        '''
        self.session = session
        try:
            with open(costs_path) as f:
                self.costs = json.load(f)
                self.no_costs = max([int(k) for k in self.costs])
        except:
            self.costs = None
            self.no_costs = 0

        try:
            with open(times_path) as f:
                self.times = json.load(f)
                self.no_times = max([int(k) for k in self.times])
        except:
            self.times = None
            self.no_times = 0

        try:
            with open(prerequisites_path) as f:
                self.prerequisites = json.load(f)
        except:
            self.prerequisites = None

        try:
            with open(exclusivity_path) as f:
                self.exclusivity = json.load(f)
        except:
            self.exclusivity = None

        try:
            with open(monetary_budgets_path) as f:
                self.monetary_budgets = json.load(f)
        except:
            self.monetary_budgets = None

        try:
            with open(time_budgets_path) as f:
                self.time_budgets = json.load(f)
        except:
            self.time_budgets = None


    def generate_coas(self,
                     project_id,
                     model_id,
                     target_objects_ids,
                     crit_metrics=['o', 'f'],
                     time_limit=300,
                     efficiency_alpha = 0.25,
                     efficiency_improvement_threshold = 0.1,
                     stop_condition = None,
                     keep_track_of_ttcs=True,
                     iterations_number_limit = 15,
                     defs_per_iteration = 1):
        '''
        return list of pairs (coa, coa_efficiency)
        '''
        result = []
        for i in range(len(crit_metrics)):
            ithresult = self._generate_coa_wrt_criticallity_score(project_id=project_id,
                                             model_id=model_id,
                                             target_objects_ids=target_objects_ids,
                                             crit_metric=crit_metrics[i],
                                             time_limit=time_limit,
                                             efficiency_alpha = efficiency_alpha,
                                             efficiency_improvement_threshold = efficiency_improvement_threshold,
                                             stop_condition = stop_condition,
                                             keep_track_of_ttcs = keep_track_of_ttcs,
                                             iterations_number_limit = iterations_number_limit,
                                             defs_per_iteration = defs_per_iteration)
            # IF keep_track_of_ttcs == True, then this is inside:
            # ithresult[0] = (coa, coa_efficiency, intermediate_ttcs)
            # intermediate_ttcs are actually final ttcs, the ones obtained when coa was implemented
            # ithresult[1] = initial_ttcs
            # ithresult[2] = number_of_iterations
            # ELSE
            # ithresult = (coa, coa_efficiency)
            if keep_track_of_ttcs == True:
                coa = ithresult[0][0]
                coa_efficiency = ithresult[0][1]
            else:
                coa = ithresult[0]
                coa_efficiency = ithresult[1]

            # messy.
            # NEED keep_track_of_ttcs = True to be able to compute efficiency wrt the same initial TTC values.
            # BUT never want to return ttcs; want list of pairs (coa, coa_efficiency) anyway

            # TODO modify the output


            if i == 0 and keep_track_of_ttcs:
                real_initial_ttcs = ithresult[1]
                result.append(ithresult[0])
            elif keep_track_of_ttcs:
                # recompute the efficiency score of this coa, wrt to the common initial ttc values
                intermediate_ttcs = ithresult[0][2]
                coa_efficiency = efficiency(real_initial_ttcs, intermediate_ttcs)
                # coa_efficiency = round(sum([efficiency_alpha * (intermediate_ttcs[x][0] - real_initial_ttcs[x][0]) +
                #                         (1 - efficiency_alpha) * (intermediate_ttcs[x][1] - real_initial_ttcs[x][1]) for x in real_initial_ttcs]), 3)

                result.append((ithresult[0][0], coa_efficiency, ithresult[0][2]))
            else:
                result.append(ithresult[0])
        if keep_track_of_ttcs:
            return (result, real_initial_ttcs, ithresult[2])

        return result


    def _generate_coa_wrt_criticallity_score(self,
                                             project_id,
                                             model_id,
                                             target_objects_ids=(),
                                             crit_metric='f',
                                             time_limit=300,
                                             efficiency_alpha = 0.25,
                                             efficiency_improvement_threshold = 0.1,
                                             stop_condition = None,
                                             keep_track_of_ttcs = False,
                                             iterations_number_limit = 15,
                                             defs_per_iteration = 1):
        '''
        TODO
        '''
        # 1. PREPROCESSING
        # 1.1 download and unzip initial model, remember its path, create corresponding Model object
        eom_file_path = self.session.download_and_unzip_model(project_id, model_id)
        eom_dir_path = eom_file_path[:eom_file_path.rindex('\\')]

        if DEBUGGING:
            print(".eom file extracted from .sCAD to {}".format(eom_file_path))

        model = Model(eom_file_path)

        if DEBUGGING:
            print("Number of objects in the model: {}".format(model.count_objects_in_the_model()))

        # 1.2 specify steps the TTC of which is to be increased. These are 'compromise' steps of target objects.
        # Need to turn objects' id's into exportedId's.
        steps_of_interest = ["{}.Compromise".format(model.get_exportedId_from_id(object_id)) for object_id in target_objects_ids]

        # 1.3 initialize variables
        coa = CoA()
        iteration = 1
        partialSolutions = {}
        defense_steps_added = set()
        coa_efficiency = 0

        if DEBUGGING:
            print('variables initialized. will run initial simulation now.')

        # 2. run initial simulations and fetch the results.
        simid, tid = self.session.run_simulation(project_id=project_id, model_id=model_id, time_limit=time_limit)

        if DEBUGGING:
            print(tid)

        initial_ttcs = {step_of_interest: self.session.get_ttcs(project_id=project_id,
                                                                simulation_id=simid,
                                                                attack_step=step_of_interest,
                                                                time_limit=time_limit) for step_of_interest in steps_of_interest}
        intermediate_ttcs = copy.deepcopy(initial_ttcs)

        if DEBUGGING:
            print("initial ttcs:")
            print(initial_ttcs)

        # 3. main loop of the algorithm starts
        while True:

            if iteration == iterations_number_limit + 1:
                break

            current_ttcs_five = set([intermediate_ttcs[x][0] for x in intermediate_ttcs])
            if current_ttcs_five == {np.inf}:
                break

            # helper variable for recognizing the defense steps added in the current iteration
            defense_steps_in_previous_coa = set(coa.hasse.nodes)

            # 3.1 fetch attack paths and merge them into a single attack graph
            attack_paths = [AttackGraph(self.session.get_attack_path_from_simulation(simulation_id=simid,
                                                                                     attack_step=step_of_interest,
                                                                                     time_limit=time_limit)) for step_of_interest in steps_of_interest]
            graph = merge_attack_graphs(attack_paths)

            if DEBUGGING:
                print('NUMBER OF NODES IN THE GRAPH: {}'.format(len(graph.nodes)))
            # clean-up: delete the scenario from securiCAD
            self.session.delete_scenario_from_project(scenario_id=tid, project_id=project_id)

            # 3.2 for every defense step, compute criticallity of the nodes it counters; assign the highest of the values
            # to the defense; sort defenses.

            # compute quality scores of defense nodes, using quality metric q3 from the paper
            graph.set_criticality_scores_of_counterable_attack_steps(metrics=crit_metric)

            quality_scores_of_defenses = {}

            for node in graph.nodes:
                if graph.nodes[node]["isDefense"]:
                    quality_scores_of_defenses[node] = graph.get_quality_scores_of_defense_step(overline_pre(pre=self.prerequisites, w = node, as_set = True), q = 3)

            defenses_sorted = sorted(quality_scores_of_defenses, key=lambda key: (quality_scores_of_defenses[key]), reverse=True)

            if DEBUGGING and False:
                print('---- quality scores for defense steps ----')
                for item in defenses_sorted:
                    print(item, quality_scores_of_defenses[item])
            # try:
            #     sorted = graph.def_nodes_sorted_by_scores(scores=crit_metric)
            # except:
            #     print('FAIL')
            #     sorted = []

            if DEBUGGING and False:
                for node in defenses_sorted:
                    print("{} what is called 'node': {}".format(5*"=", node))
                    print(graph.nodes[node]['scores'],
                          '\t',
                          graph.nodes[node]["eid"],
                          #graph.nodes[node]["name"],
                          graph.nodes[node]["stepname"])
                    print()

            # 3.3 iterate over the defense steps. for each, try to add it and all of its prerequisites to the coa.
            if DEBUGGING:
                print('Step 3.3.')

            number_of_defense_steps_added = 0

            while defenses_sorted != []:

                node = defenses_sorted.pop(0)
            #for node in sorted:

                if DEBUGGING:
                    print(node)

                # for future code optimization: exclusivity and monetary constraints could be checked before a new CoA object is constructed
                if self.prerequisites is None:
                    new_coa = coa.add_from_dict({node: []})
                else:
                    new_coa = coa.add_from_dict(overline_pre(self.prerequisites, node))
                new_coa_nodes_as_set = set(new_coa.hasse.nodes)

                if DEBUGGING:
                    print(new_coa_nodes_as_set)

                # check exclusivity
                exclusivity_satisfied = True
                if self.exclusivity is not None:
                    for node in new_coa_nodes_as_set:
                        if node in self.exclusivity and set(self.exclusivity[node]).intersection(new_coa_nodes_as_set) != set():
                            exclusivity_satisfied = False
                            break
                if exclusivity_satisfied == False:
                    # move to the next candidate defense step
                    continue

                # check costs
                if self.costs is not None or self.times is not None:
                    costs, times = self._get_formatted_prices_for_computations(new_coa_nodes_as_set)

                # check monetary costs
                monetary_budgets_satisfied = True
                if self.monetary_budgets is not None and self.costs is not None:
                    monetary_costs_of_new_coa = new_coa.compute_costs_and_times(costs = costs)
                    for i in range(self.no_costs):
                        if monetary_costs_of_new_coa[i] > self.monetary_budgets[str(i+1)]:
                            monetary_budgets_satisfied = False
                            break
                if monetary_budgets_satisfied == False:
                    # move to the next candidate defense step
                    continue

                # check time-like costs
                time_like_budgets_satisfied = True
                if self.time_budgets is not None and self.times is not None:
                    time_like_costs_of_new_coa = new_coa.compute_costs_and_times(costs=[], times=times)
                    for j in range(self.no_times):
                        if time_like_costs_of_new_coa[j] > self.time_budgets[str(j+1)]:
                            time_like_budgets_satisfied = False
                            break
                if time_like_budgets_satisfied == False:
                    # move to the next candidate defense step
                    continue

                # will arrive here if all the constraints are satisfied
                coa = new_coa
                defense_steps_added = set(coa.hasse.nodes).difference(defense_steps_in_previous_coa)
                number_of_defense_steps_added += len(defense_steps_added)
                if number_of_defense_steps_added >= defs_per_iteration:
                    break

                # remove the attack steps from the set of counterable attack steps
                # UNABLE TO DO THIS PROPERLY
                # what should be done:
                # 1. remove the ones countered by selected defenses
                # 2. remove their AND children
                # 3. remove their AND children
                # etc.
                # then update the graph and recompute quality scores, ffs

                # QUICK FIX :):):):)
                # 1. remove attack steps DIRECTLY countered by added defenses, as well as the defenses

                # TODO: maybe comment out the part on updating the attack graph, since the defenses in
                # securiCAD don't block steps completely. Run tests: commented out vs not and see the efficiencies.

                if DEBUGGING:
                    print('updating graph and recomputing quality of defenses')
                    update_start = time.time()

                to_remove=[]
                for step in defense_steps_added:
                    if step in graph.nodes:
                        for node in graph.successors(step):
                            if node not in to_remove:
                                to_remove.append(node)
                        to_remove.append(step)

                for node in to_remove:
                    if node in defenses_sorted:
                        defenses_sorted.remove(node)
                    graph.remove_node(node)

                # removing attack steps might result in some defense steps having no successors, so remove them as well
                to_remove = []
                for node in graph.nodes:
                    if graph.nodes[node]["isDefense"] and [child for child in graph.successors(node)] == [] and node not in to_remove:
                        to_remove.append(node)
                for node in to_remove:
                    if node in defenses_sorted:
                        defenses_sorted.remove(node)
                    graph.remove_node(node)
                # 2. recompute scores for defense steps; DOESN'T REALLY MAKE SENSE, as the counterable attack steps
                # migth be no longer reachable by the attacker, but better than nothing.
                graph.set_criticality_scores_of_counterable_attack_steps(metrics=crit_metric)
                quality_scores_of_defenses = {}
                for node in defenses_sorted:
                    quality_scores_of_defenses[node] = graph.get_quality_scores_of_defense_step(overline_pre(pre=self.prerequisites, w = node, as_set = True), q = 3)

                defenses_sorted = sorted(quality_scores_of_defenses, key=lambda key: (quality_scores_of_defenses[key]), reverse=True)

                if DEBUGGING:
                    update_end = time.time()
                    print('updating graph and recomputing quality took {} seconds'.format(update_end-update_start))

            # 3.4 at this point, a (possibly empty or the same as the last one) CoA has been constructed.
            if  defense_steps_added == set():
                # no changes made to the coa, so nothing new will happen. Terminate the main loop.
                break

            if DEBUGGING:
                print('Defense steps added: {}'.format(defense_steps_added))

            # else: new coa constructed. compute its efficiency metric and store it. To compute the efficiency metric, need to run simulations.
            #
            # 4. compute the efficiency score of the new coa
            # 4.1 update the model (locally) by turning the defenses in the coa on
            for defense_step in defense_steps_added:

                if DEBUGGING:
                    print('will try to activate the defense {}'.format(defense_step))

                model.turn_defense_on(objectExportedID=defense_step.split('.')[1], defenseName=defense_step.split('.')[-1])

            if DEBUGGING:
                print('Finished activating defenses.')

            defense_steps_added = set()

            # 4.2 zip&upload the new model
            # write to .eom file
            model.write_to_file(new_path=eom_file_path)
            modified_model_id = self.session.zip_and_upload_model(path_to_dir_with_model_files=eom_dir_path, project_id=project_id)

            if DEBUGGING:
                print('Zipped and uploaded.')

            if DEBUGGING:
                pass
                #print('will sleep for 3 minutes now')
                #time.sleep(3*60)

            # 4.3 run simulations on the new model
            simid, tid = self.session.run_simulation(
                    project_id=project_id, model_id=modified_model_id, time_limit=time_limit)
            # fetch new ttc values
            intermediate_ttcs = {step_of_interest: self.session.get_ttcs(
                    project_id=project_id, simulation_id=simid, attack_step=step_of_interest, time_limit=time_limit) for step_of_interest in steps_of_interest}
            if DEBUGGING:
                print('intermediate ttc values: {}'.format(intermediate_ttcs))
            # compute efficiency score of the coa
            coa_efficiency = efficiency(initial_ttcs, intermediate_ttcs)
            # coa_efficiency = round(sum([efficiency_alpha * (intermediate_ttcs[step_of_interest][0] - initial_ttcs[step_of_interest][0]) +
            #                             (1 - efficiency_alpha) * (intermediate_ttcs[step_of_interest][1] - initial_ttcs[step_of_interest][1]) for step_of_interest in steps_of_interest]), 3)

            # 5. update variables
            if keep_track_of_ttcs:
                partialSolutions[iteration] = (coa, coa_efficiency, intermediate_ttcs)
            else:
                partialSolutions[iteration] = (coa, coa_efficiency)
            iteration += 1

            # 6. clean-up: delete the modified model from the project
            self.session.delete_model_from_project(model_id=modified_model_id, project_id=project_id)


            if DEBUGGING:
                print(coa_efficiency)

        # :(
        try:
            self.session.delete_scenario_from_project(scenario_id=tid, project_id=project_id)
        except:
            pass

        # 7. backtracking to get the final solution from the set of partial solutions
        # at this point, the solution generated in the last iteration is 'coa' and its efficiency is 'coa_efficiency'.
        if DEBUGGING:
            print("BACKTRACKING")

            for i in partialSolutions:
                print(i)
                print(partialSolutions[i][0].hasse.nodes)
                print(partialSolutions[i][1])
                print(15*"=")

        if iteration == 2 or coa_efficiency == 0:
            if keep_track_of_ttcs:
                return ((coa, coa_efficiency, intermediate_ttcs), initial_ttcs, iteration-1)
            else:
                return (coa, coa_efficiency)
        for i in partialSolutions:
            relative_improvement = abs((coa_efficiency - partialSolutions[i][1])/coa_efficiency)
            if relative_improvement < efficiency_improvement_threshold:
                if keep_track_of_ttcs:
                    #print((partialSolutions[i], initial_ttcs))
                    return (partialSolutions[i], initial_ttcs, iteration-1)
                else:
                    return partialSolutions[i]

        # if we get to this line, something went wrong
        print('If you see this, something went wrong.')
        return


    def _prices_of_step_in_coa(self, v, nodes):
        '''
        given set 'nodes' of nodes in a coa that 'v' belongs to, parse self.costs and self.times dictionaries
        to get the prices of 'v' in the context of this CoA. that is, compute the prices, taking the possible
        dependencies into account.

        return two lists of floats. using the notation from the paper, the first of the lists is
        [Cost_1(v, D), ..., Cost_n(v, D)], and the second one is
        [Time_1(v, D), ..., Time_m(v, D)], with D = 'nodes'.

        if neither of the "costs" is specified, return None

        if exactly one of them is not specified, the corresponding list will be empty
        '''
        if self.costs is None:
            if self.times is None:
                return None
            else:
                return [], self._get_prices_from_dict(v, nodes, "times")
        else:
            if self.times is None:
                return self._get_prices_from_dict(v, nodes, "costs"), []
            else:
                return self._get_prices_from_dict(v, nodes, "costs"), self._get_prices_from_dict(v, nodes, "times")


    def _get_prices_from_dict(self, v, nodes, dict_name="costs", default =  0):
        '''
        compute prices for implementation of defense step 'v' in the context of coa consisting of defense steps in 'nodes';
        prices in the sense of the specified resources (dict_name = "costs" or dict_name = "times")

        if node does not appear in the dictionary, it will get the 'default' value
        '''
        if dict_name == 'costs':
            d = self.costs
            number_of_resources = self.no_costs
        elif dict_name == 'times':
            d = self.times
            number_of_resources = self.no_times
        else:
            print("Wrong name of resources given. Abort!")
            return

        result = []
        for i in range(1,number_of_resources+1):
            if v not in d[str(i)]:
                result.append(default)
                continue
            ith_cost_of_v = d[str(i)][v]
            # case 1: no dependencies; the value is a number
            if isinstance(ith_cost_of_v, int) or isinstance(ith_cost_of_v, float):
                result.append(ith_cost_of_v)
                continue
            # case 2: there are dependencies
            else:
                assert isinstance(ith_cost_of_v, dict)
                ith_cost = ith_cost_of_v["default"]
                # step 1: go through dependencies on steps of the same "type", if any
                if "same_type_dependency" in ith_cost_of_v:
                    counter = 0
                    # recall: steps are of the form "class.eid.object_name.step_name"
                    class_of_object_v_applied_to = v.split('.')[0]
                    name_of_defense_that_v_represents = v.split('.')[-1]
                    for step in nodes:
                        if step.split('.')[0] == class_of_object_v_applied_to and step.split('.')[-1] == name_of_defense_that_v_represents:
                            counter += 1
                max_key_val = max([int(k) for k in ith_cost_of_v["same_type_dependency"].keys()])
                ith_cost = ith_cost_of_v["same_type_dependency"][str(min(counter,max_key_val))]
                # step 2: go through dependencies on steps of different type, if any
                if "different_type_dependency" in ith_cost_of_v:
                    for step in ith_cost_of_v["different_type_dependency"]:
                        if step in nodes:
                            # value is of the form "*float", "+float" or "-float"
                            full_value = ith_cost_of_v["different_type_dependency"][step]
                            symbol = full_value[0]
                            numeric_value = float(numeric_value[1:])
                            if symbol == '*':
                                ith_cost *= numeric_value
                            elif symbol == '+':
                                ith_cost += numeric_value
                            elif symbol == '-':
                                ith_cost -= numeric_value
                            else:
                                # if the input is formatted properly, this line shouldn't execute
                                continue
                # add the cost to the result
                result.append(ith_cost)
        return result


    def _get_formatted_prices_for_computations(self, steps_in_coa):
        costs =[{} for i in range(self.no_costs)]
        times = [{} for j in range(self.no_times)]
        for v in steps_in_coa:
            v_cost_prices, v_time_prices = self._prices_of_step_in_coa(v, steps_in_coa)
            for i in range(self.no_costs):
                costs[i][v] = v_cost_prices[i]
            for j in range(self.no_times):
                times[j][v] = v_time_prices[j]
        return costs, times


def overline_pre(pre, w, as_set = False):
    '''
    Constructs a dictionary containing w, its prerequisites as specified by 'pre',
    the prerequisites of w's prerequisites, etc.

    This object is denoted by \overline{Pre} in the paper.

    If as_set is set to True, return the set containing all the steps in the dictionary.
    '''
    to_be_processed = set([w])
    result = {}
    while to_be_processed != set():
        processed_element = to_be_processed.pop()
        try:
            prerequisites_for_the_element = pre[processed_element]
        except:
            result[processed_element] = []
            continue
        result[processed_element] = prerequisites_for_the_element
        to_be_processed = to_be_processed.union(set(prerequisites_for_the_element))
    if as_set:
        result_as_set = set()
        for item in result:
            result_as_set = result_as_set.union(set([item]))
            result_as_set = result_as_set.union(set(result[item]))
        return result_as_set
    return result


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
        if initial[x][0] != np.inf:
            if initial[x][1] == np.inf:
                # ttc5_i is finite, ttc50_i is not
                result += np.power(1.05, -initial5) * min(final5-initial5, c)
            else:
                # ttc5_i is finite, ttc50_i is also finite
                result += np.power(1.05, -initial5) * min(final5-initial5, c) + np.power(1.05, -initial50) * min(final50-initial50, c)
    return round(result,3)