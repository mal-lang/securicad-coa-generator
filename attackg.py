import json

import networkx as nx

p_test = False

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
        for node in path[target]["nodes"]:
            if node["isDefense"] == True:
                # get all the defenses (classdefs) for the corresponding class object
                classdefs = metadata["assets"][node["class"]]["defenses"]
                # find info for one defense from classdefs.
                for d in classdefs:
                    # name of that particular defense = attackstep value for the path node
                    if d["name"] == node["attackstep"]:
                        if "suppress" not in d["tags"]:
                            mapping[node["index"]] = node["id"]
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


    def find_critical_attack_step(self, metric):
        print("\nCriticality of Attack steps")
        metrics_for_nodes = {}
        if metric == 'f':
            for node in self.nodes:
                if not self.nodes[node]["isDefense"]:
                    metrics_for_nodes[node] = self.nodes[node]["frequency"]
                    #debug
                    print("NODE :", node, "  Frequency :", metrics_for_nodes[node])
        else:
            weighted_out_degrees = {}
            for node in self.nodes:
                if not self.nodes[node]["isDefense"]:
                    for child in self.successors(node):
                        weighted_out_degrees[node] = sum(self.nodes[child]["frequency"])
            if metric == 'o':
                metrics_for_nodes = weighted_out_degrees
            # we can put code for other metrics here like frequency-out degree combinations

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
        print("\nSorted Nodes with Criticality Scores")
        for node in self.nodes_sorted:
            print(self.nodes[node]["id"], "\t", self.nodes[node]["crit_score"])
        return


    def find_best_defense(self, meta_lang, model_dict_list, budget_remaining):
        print("\nAnalyzing critical attack step to get suitable defense")
        for top_attack_step in self.nodes_sorted:
            block_range_def = {}
            no_of_def_for_i_node = 0
            pred_nodes = []
            print(top_attack_step)
            for pred_node in self.predecessors(top_attack_step):
                pred_nodes.append(pred_node)
                if self.nodes[pred_node]["isDefense"]:
                    print("This is the most critical attack step with Defense")
                    no_of_def_for_i_node += 1
                    block_range_def[pred_node] = sum([self.nodes[child]["frequency"] for child in self.successors(pred_node)])
                    print("Candidate defense node:", pred_node, "  Total frequency blocked:", block_range_def[pred_node])
            if no_of_def_for_i_node > 0:
                for no_def in range(no_of_def_for_i_node):
                    best_def = max(block_range_def, key=block_range_def.get)
                    print("Best defense detected:", best_def)
                    print("Budget check ...")
                    flag = 0
                    for node in self.nodes:
                        if self.nodes[node]["id"] == best_def:
                            if p_test:
                                print("t - 1")
                            print("TAG check")
                            for model_dict in model_dict_list:
                                if p_test:
                                    print("t - 2")
                                if self.nodes[node]["name"] == model_dict["name"]:
                                    if p_test:
                                        print("t - 3")
                                    def_cost = model_dict["attributesJsonString"]
                                    for key in def_cost:
                                        if p_test:
                                            print("t - 4")
                                        if self.nodes[node]["attackstep"] == key:
                                            if p_test:
                                                print("t - 5")
                                            if budget_remaining > int(def_cost[key]):
                                                changed_budget = budget_remaining - int(def_cost[key])
                                                print("Cost of defense: ", def_cost[key])
                                                print("Apply the defense : AS TAG COST < BUDGET")
                                                return self.nodes[node], changed_budget
                                            else:
                                                flag = 1
                                                print("Cost of defense: ", def_cost[key])
                                                print("Out of budget")
                                                block_range_def[best_def] = 0 #if both costs are high or no cost given
                                                break
                                if flag == 1:
                                    break
                            if flag == 1:
                                break
                            if p_test:
                                print("t - 13")
                            print("Infostring check")
                            classdefs = meta_lang["assets"][self.nodes[node]["class"]]["defenses"]
                            defense_info = next((d for d in classdefs if d["name"] == self.nodes[node]["attackstep"]), False)
                            try:
                                def_class_cost = json.loads(defense_info["metaInfo"]["cost"])
                                if budget_remaining > int(def_class_cost["first_use"]):  # TODO for susequent use
                                    if p_test:
                                        print("t - 14")
                                    changed_budget = budget_remaining - int(def_class_cost["first_use"])
                                    print("Cost of defense: ", def_class_cost["first_use"])
                                    print("Apply the defense : AS INFOSTRING COST < BUDGET")
                                    return self.nodes[node], changed_budget
                                else:
                                    flag = 1
                                    if p_test:
                                        print("t - 15")
                                    print("Cost of defense: ", def_class_cost["first_use"])
                                    print("Out of budget")
                                    block_range_def[best_def] = 0  # if both costs are high or no cost given
                                    break
                            except: print("No tag or cost infostring")
                        if flag == 1: #TODO when the defense is out of budget wrt top_attack_step (can be improved - once a defense out of budget it should be removed totally)
                            break
                    block_range_def[best_def] = 0  # if both costs are high or no cost given
            else:
                print("Defense not available for Attack step:", top_attack_step)



def merge_attack_graphs(graphs):
    res = AttackGraph()
    freq_of_i = {}
    print("\nNumber of graphs sent to Merge - ", len(graphs))
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
            res.nodes[node]["frequency"] = freq_of_i[node] + graphs[i].nodes[node]["frequency"]
    return res

