import json
import os
import networkx as nx
from random import randint
from random import seed


seed(1)
p_test = True
JSON_FILENAME = "results.json"

def read_json_file(filename):
    if os.path.isfile(filename):
        with open(filename, 'r') as json_file:
            return json.load(json_file)
    else:
        return {}


def write_json_file(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

class AttackGraph(nx.DiGraph):

    def __init__(self, path = None, target = None, metadata = None):
        self.nodes_sorted = []
        super().__init__()
        self._get_params_from_json(path, target, metadata)


    def _get_params_from_json(self, path = None, target = None, metadata = None):
        if path is None:
            return
        # finding out the edges by index values
        edges_by_indices = []
        for link in path[target]["links"]:
            edges_by_indices.append((link["source"], link["target"]))
        # map index to id
        mapping = {}
        #print("The path is", path)
        for node in path[target]["nodes"]:
            #print(node)
            if node["isDefense"] == True:
                # get all the defenses (classdefs) for the corresponding class object
                classdefs = metadata["assets"][node["class"]]["defenses"]
                #print(classdefs)
                # find info for one defense from classdefs.
                for d in classdefs:
                    # name of that particular defense = attackstep value for the path node
                    if d["name"] == node["attackstep"]:
                        if "suppress" not in d["tags"]:
                            mapping[node["index"]] = node["id"]
                            #print(mapping)
                            continue
            else:
                mapping[node["index"]] = node["id"]
        # transform edges from index to id
        edges_by_ids = []
        for edge in edges_by_indices:
            # only if both the nodes in edges are in mapping dict then append those edges in edges_by_ids
            if mapping.get(edge[0],False) and mapping.get(edge[1],False):
                edges_by_ids.append((mapping[edge[0]], mapping[edge[1]]))
        self.add_edges_from(edges_by_ids)
        for node in path[target]["nodes"]:
            # only those nodes which are mapped that means are nor suppressed
            if mapping.get(node["index"],False):
                # as name field is given as example - (32) Given Name; and we only need the "Given Name"
                temp = node["name"]
                object_name = temp[temp.index(' ')+1:]
                self.nodes[node["id"]]["id"] = node["id"]
                self.nodes[node["id"]]["index"] = node["index"]
                self.nodes[node["id"]]["eid"] = node["eid"]
                self.nodes[node["id"]]["name"] = object_name
                self.nodes[node["id"]]["class"] = node["class"]
                self.nodes[node["id"]]["attackstep"] = node["attackstep"]
                self.nodes[node["id"]]["frequency"] = node["frequency"]
                self.nodes[node["id"]]["isDefense"] = node["isDefense"]
                self.nodes[node["id"]]["ttc"] = node["ttc"]
                #print(self.nodes[node["id"]]["id"], self.nodes[node["id"]]["index"], self.nodes[node["id"]]["eid"], self.nodes[node["id"]]["name"], self.nodes[node["id"]]["class"], self.nodes[node["id"]]["attackstep"], self.nodes[node["id"]]["frequency"], self.nodes[node["id"]]["isDefense"], self.nodes[node["id"]]["ttc"])


    def find_critical_attack_step(self, metric):
        print("\nCriticality of Attack steps")
        metrics_for_nodes = {}
        #print(self.nodes)
        if metric == 'f':
            for node in self.nodes:
                if not self.nodes[node]["isDefense"]:
                    metrics_for_nodes[node] = self.nodes[node]["frequency"]
                    #debug
                    #print("NODE :", node, "  Frequency :", metrics_for_nodes[node])         ##########################################
        else:
            weighted_out_degrees = {node: [sum([self.nodes[child]["frequency"] for child in self.successors(node)])] for
                                    node in self.nodes}
            if metric == 'o':
                metrics_for_nodes = weighted_out_degrees
        '''else:
            weighted_out_degrees = {}
            for node in self.nodes:
                if not self.nodes[node]["isDefense"]:
                    for child in self.successors(node):
                        weighted_out_degrees[node] = sum(self.nodes[child]["frequency"])
            if metric == 'o':
                metrics_for_nodes = weighted_out_degrees
            # we can put code for other metrics here like frequency-out degree combinations'''

        # sorting is done depending on the metrics
        if len(metric) == 1: # for 'f' and 'o' and not for 'fo' or 'of'
            self.nodes_sorted = sorted(metrics_for_nodes, key=lambda key: (metrics_for_nodes[key]), reverse=True)
            #debug
            print("\nSorted Nodes")
            print(self.nodes_sorted)
        # we can put code for other metrics here like frequency-out degree combinations with metric length 2

        # assigning scores high to low on nodes according to the sorted order
        score = len(self.nodes_sorted)
        metric_of_previous_node = None
        for node in self.nodes_sorted:
            if metric_of_previous_node is None:
                # score is being assigned to the most critical attack step
                self.nodes[node]["crit_score"] = score
            else:
                if metrics_for_nodes[node] == metric_of_previous_node:
                    # the metric of this node is the same as the previous one, so it will get the same criticality score
                    self.nodes[node]["crit_score"] = score
                else:
                    self.nodes[node]["crit_score"] = score - 1
                    score -= 1
            metric_of_previous_node = metrics_for_nodes[node]
        #debug
        print("\nSorted Nodes with Criticality Scores Print")
        #for node in self.nodes_sorted:
            #print(self.nodes[node]["id"], "\t", self.nodes[node]["crit_score"]) #################################################
        return


    def find_best_defense(self, meta_lang, model_dict_list, budget_remaining):
        data = read_json_file(JSON_FILENAME)
        print(data)

        # if "monetary_cost" not in data["CoAs"][coa_index].keys():
        #     tmpd["monetary_cost"] = {}
        # if "defenses" not in data.keys():
        #     tmpd["defenses"] = {}

        print("\nAnalyzing critical attack step to get suitable defense")
        No_of_times_used=0
        def_cost_list_dict={}
        for top_attack_step in self.nodes_sorted:
            block_range_def = {}
            no_of_def_for_i_node = 0
            pred_nodes = []
            print("Attack Step:", top_attack_step)
            for pred_node in self.predecessors(top_attack_step):
                #print("Pred Nodes ", pred_node)
                pred_nodes.append(pred_node)
                if self.nodes[pred_node]["isDefense"]:
                    print("This is the most critical attack step with Defense")
                    no_of_def_for_i_node += 1
                    block_range_def[pred_node] = sum([self.nodes[child]["frequency"] for child in self.successors(pred_node)])
                    print("Candidate defense node:", pred_node, "  Total frequency blocked:", block_range_def[pred_node])
            #print("no_of_def_for_i_node", no_of_def_for_i_node)
            #print(block_range_def)
            # Enter if ...
            if no_of_def_for_i_node > 0:
                for no_def in range(no_of_def_for_i_node):
                    best_def = max(block_range_def, key=block_range_def.get)
                    #print(key)
                    print("Best defense detected:", best_def)
                    print("Budget check ...")
                    not_enough_budget = False
                    for node in self.nodes:
                        #print(self.nodes[node]["name"], self.nodes[node]["id"])
                        if self.nodes[node]["id"] == best_def:
                            if p_test:
                                print("1 - Defense Name: ", best_def)

                            # Checking if user specified cost tags
                            for idx,model_dict in enumerate(model_dict_list):
                                # print(model_dict)
                                # print(self.nodes[node])
                                if self.nodes[node]["name"] == model_dict["name"]:
                                    if p_test:
                                        print("Name of the Object and Associated Defense: ", self.nodes[node]["name"], model_dict["attributesJsonString"])
                                    def_costs = model_dict["attributesJsonString"]
                                    print("Printing Tag Dictionary")
                                    print(def_costs)

                                    cost_mc=[]
                                    cost_tc=[]


                                    this_cost_mc = None
                                    this_cost_tc = None
                                    #print(def_costs)

                                    # Check all tags associated to the defense
                                    for key in def_costs:
                                        # If the tag has the same name of the defense
                                        if self.nodes[node]["attackstep"] == key[:-3]:
                                            # If the tag ends with "_mc"
                                            if key[-3:] == '_mc':
                                                cost_mc = def_costs[key].split(" ")
                                                print("MC Cost", cost_mc)
                                                if len(cost_mc) > 1:
                                                    print("MC Cost is longer than one element")
                                                    this_cost_mc = cost_mc.pop(0)
                                                    print("This time is using ", this_cost_mc)
                                                    new_cost_mc_list = " ".join(cost_mc)
                                                    model_dict_list[idx]["attributesJsonString"][key] = new_cost_mc_list
                                                    print("The joined list is:")
                                                    print(new_cost_mc_list)
                                                    print("NOW THE ARRAY MC COST WILL BE:")
                                                    print(model_dict_list[idx]["attributesJsonString"][key])
                                                    #print(model_dict_list[idx])
                                                else:
                                                    print("MC Cost is one element")
                                                    this_cost_mc = cost_mc[0]
                                                    print("This time is using ", this_cost_mc)
                                                    print("The joined list is:")
                                                    print([this_cost_mc])
                                                    model_dict_list[idx]["attributesJsonString"][key] = [this_cost_mc]
                                                    print("NOW THE ARRAY MC COST WILL BE:")
                                                    print(model_dict_list[idx]["attributesJsonString"][key])
                                            # If the tag ends with "_tc"
                                            elif key[-3:] == "_tc":
                                                cost_tc = def_costs[key].split(" ")
                                                #print("TC cost ", cost_tc)
                                                if len(cost_tc) > 1:
                                                    #print("TC Cost is longer than one element")
                                                    this_cost_tc = cost_tc.pop(0)
                                                    #print("This time is using ", this_cost_tc)
                                                    new_cost_tc_list = " ".join(cost_tc)
                                                    model_dict_list[idx]["attributesJsonString"][key] = new_cost_tc_list
                                                    #print("The joined list is:")
                                                    #print(new_cost_tc_list)
                                                    #print("NOW THE ARRAY TC COST WILL BE:")
                                                    #print(model_dict_list[idx]["attributesJsonString"][key])
                                                else:
                                                    #print("TC Cost is one element")
                                                    this_cost_mc = cost_tc[0]
                                                    #print("This time is using ", this_cost_tc)
                                                    #print("The joined list is:")
                                                    #print([this_cost_tc])
                                                    model_dict_list[idx]["attributesJsonString"][key] = [this_cost_tc]
                                                    #print("NOW THE ARRAY TC COST WILL BE:")
                                                    #print(model_dict_list[idx]["attributesJsonString"][key])
                                   
                                        if p_test:
                                            print("Monetary Cost: ", this_cost_mc)
                                        # cost_used=def_cost_list_dict[self.nodes[node]["name"]][0][No_of_times_used]
                                        if this_cost_mc:
                                            print("The suggested defense is: ", key[:-3])
                                            #print("The Ref value of Defense is: ", def_costs["ref"])
                                            print("The Monetary Cost of defense: ", this_cost_mc)
                                            monetary_cost = json.dumps(this_cost_mc)

                                            results = '"Monetary Cost of defense is: " {} \n'.format(monetary_cost)
                                            # final_result["monetary_cost"] = monetary_cost
                                            with open('newTestsResults.txt', 'a') as f:
                                                f.write(results)
                                            defense_detail = json.dumps(key[:-3])
                                            results = '"Name of defense is: " {} \n'.format(defense_detail)
                                            with open('newTestsResults.txt', 'a') as f:
                                                f.write(results)

                                            if budget_remaining > int(this_cost_mc):
                                                changed_budget = budget_remaining - int(this_cost_mc)

                                                data["CoAs"].append({})
                                                data["CoAs"][-1]["monetary_cost"] = {"1": int(this_cost_mc)}


                                                data["CoAs"][-1]["defenses"] = []
                                                if len(data["CoAs"]) > 1:
                                                    data["CoAs"][-1]["defenses"] = data["CoAs"][-2]["defenses"].copy()
                                                    data["CoAs"][-1]["defenses"].append({"ref": str(randint(1, 100)), "defensename":  key[:-3], "defenseInfo":  key[:-3] + " is used"})
                                                else:
                                                    data["CoAs"][-1]["defenses"].append({"ref": str(randint(1, 100)), "defensename":  key[:-3], "defenseInfo":  key[:-3] + " is used"})


                                                # if len(data["CoAs"][coa_index]["monetary_cost"].keys()) > 0:
                                                #     print("THE MONETARY COST DICTIONARY HAS ALREADY A KEY")
                                                #     max_key = max([int(x) for x in data["CoAs"][coa_index]["monetary_cost"].keys()])
                                                #     print("THE MAX KEY IS")
                                                #     print(max_key)
                                                #     data["CoAs"][coa_index]["monetary_cost"][str(max_key+1)] = int(this_cost_mc)
                                                #     print("NOW THE MONETARYA COST DICTIONARY IS :")
                                                #     print(data["CoAs"][coa_index]["monetary_cost"])
                                                # else:
                                                #     print("THE MONETARY COST DICTIONARY HAS NO KEYS")
                                                #     data["CoAs"][coa_index]["monetary_cost"]["1"] = int(this_cost_mc)
                                                #     print("NOW THE MONETARYA COST DICTIONARY IS :")
                                                #     print(data["CoAs"][coa_index]["monetary_cost"])
                                                write_json_file(JSON_FILENAME, data)
                                            
                                                #print("Time Cost of defense: ", this_cost_tc)
                                                print("Apply the defense : AS TAG COST < BUDGET")
                                                return self.nodes[node], changed_budget
                                            else:
                                                not_enough_budget = True
                                                print("Out of budget")
                                                # print(block_range_def[best_def])
                                                block_range_def[best_def] = 0  # if both costs are high or no cost given
                                                break

                                if not_enough_budget:
                                    break
                            if not_enough_budget:
                                break
                            print(">> SINCE NO USER SPECIFIED TAGS HAVE BEEN FOUND, WE CHECK THE JSON LANGUAGE MODEL")
                            print("JSON Infostring check")
                            classdefs = meta_lang["assets"][self.nodes[node]["class"]]["defenses"]
                            defense_info = next((d for d in classdefs if d["name"] == self.nodes[node]["attackstep"]), False)
                                #print(classdefs)
                                #print(defense_info)
                            try:
                                def_class_cost = defense_info["metaInfo"]["cost"]
                                def_class_cost_time = defense_info["metaInfo"]["cost_time"]
                                def_name = defense_info["name"]
                                print(">>I found the defense in the JSON ")
                                print(">>ANALYZING: ", def_name)
                                #print("Time cost ", def_class_cost_time)
                                current_mc = None
                                current_tc = None

                                print(">>MC array for this Defense before application is:", def_class_cost)
                                #print(">>TC array for this Defense before application is:", def_class_cost_time)

                                if len(def_class_cost) > 1:
                                    current_mc = def_class_cost.pop(0)
                                else:
                                    current_mc = def_class_cost[0]

                                if len(def_class_cost_time) > 1:
                                    current_tc = def_class_cost_time.pop(0)
                                else:
                                    current_tc = def_class_cost_time[0]

                                print(">>MC current cost used for this Defense is:", current_mc)
                                #print(">>TC current cost used for this Defense now is:", current_tc)

                                print(">>MC array for this Defense now is:", def_class_cost)
                                #print(">>TC array for this Defense now is:", def_class_cost_time)

                                if budget_remaining > current_mc:
                                    print(">>AFFORDABLE DEFENSE: REMAINING BUDGET  > MONETARY COST")
                                    changed_budget = budget_remaining - current_mc
                                    monetary_cost = json.dumps(current_mc)
                                    results = '"Monetary Cost of defense is: " {} \n'.format(monetary_cost)

                                    data["CoAs"].append({})
                                    data["CoAs"][-1]["monetary_cost"] = {"1": int(current_mc)}



                                    data["CoAs"][-1]["defenses"] = []
                                    if len(data["CoAs"]) > 1:
                                        data["CoAs"][-1]["defenses"] = data["CoAs"][-2]["defenses"].copy()
                                        data["CoAs"][-1]["defenses"].append({"ref": str(randint(1, 100)), "defensename": def_name, "defenseInfo": def_name + " is used" })
                                    else:
                                        data["CoAs"][-1]["defenses"].append({"ref": str(randint(1, 100)), "defensename": def_name, "defenseInfo": def_name + " is used" })

                                    # if len(data["CoAs"][coa_index]["monetary_cost"].keys()) > 0:
                                    #     print("THE MONETARY COST DICTIONARY HAS ALREADY A KEY")
                                    #     max_key = max([int(x) for x in data["CoAs"][coa_index]["monetary_cost"].keys()])
                                    #     print("THE MAX KEY IS")
                                    #     print(max_key)
                                    #     data["CoAs"][coa_index]["monetary_cost"][str(max_key+1)] = int(current_mc)
                                    #     print("NOW THE MONETARYA COST DICTIONARY IS :")
                                    #     print(data["CoAs"][coa_index]["monetary_cost"])
                                    # else:
                                    #     print("THE MONETARY COST DICTIONARY HAS NO KEYS")
                                    #     data["CoAs"][coa_index]["monetary_cost"]["1"] = int(current_mc)
                                    #     print("NOW THE MONETARYA COST DICTIONARY IS :")
                                    #     print(data["CoAs"][coa_index]["monetary_cost"])
                                    write_json_file(JSON_FILENAME, data)


                                    with open('newTestsResults.txt', 'a') as f:
                                        f.write(results)
                                    print("Monetary Cost of defense: ", def_name, "is ", current_mc)
                                    results = '"Name of defense is: " {} \n'.format(def_name)
                                    with open('newTestsResults.txt', 'a') as f:
                                        f.write(results)
                                    #print("Time Cost of defense: ", def_name, "is ", current_tc)
                                    print("Apply the defense : AS INFOSTRING COST < BUDGET")
                                    #print(self.nodes[node])
                                    return self.nodes[node], changed_budget
                                else:
                                    print(">>INSUFFICIENT BUDGET: REMAINING BUDGET  < MONETARY COST")
                                    not_enough_budget = True
                                    print("Cost of defense: ", current_mc)
                                    print("Out of budget")
                                    block_range_def[best_def] = 0  # if both costs are high or no cost given
                                    break
                                #if budget_remaining > int(def_class_cost_time["first_use"]):
                                    #print("Time Cost", def_class_cost_time["first_use"])
                            except: 
                                print("No tag or cost infostring")
                        if not_enough_budget: #TODO when the defense is out of budget wrt top_attack_step (can be improved - once a defense out of budget it should be removed totally)
                            break
                    block_range_def[best_def] = 0  # if both costs are high or no cost given
            else:
                print("Defense not available for Attack step:", top_attack_step)

            #print("Pred_Node", pred_nodes)



def merge_attack_graphs(graphs):
    res = AttackGraph()
    freq_of_i = {}
    print("\nNumber of graphs sent to Merge - ", len(graphs))
    #print(graphs[0].nodes)
    print("Change of NetworkX Graph Status")
    for i in range(len(graphs)):
        for node in graphs[i].nodes:
            if node in res.nodes:
                freq_of_i[node] = res.nodes[node]["frequency"]
            else:
                freq_of_i[node] = 0
        res = nx.algorithms.operators.binary.compose(res, graphs[i])
        print(res.nodes)
        for node in graphs[i].nodes:
            #print(graphs[i].nodes[node]["frequency"])
            res.nodes[node]["frequency"] = freq_of_i[node] + graphs[i].nodes[node]["frequency"]
    return res

