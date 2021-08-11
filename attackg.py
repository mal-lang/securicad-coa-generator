import networkx as nx

class AttackGraph(nx.DiGraph):

    def __init__(self, path = None, target = None):
        self.nodes_sorted = []
        super().__init__()
        self._get_params_from_json(path, target)

    def _get_params_from_json(self, path = None, target = None):
        if path is None:
            return
        # finding out the edges by index values
        edges_by_indices = []
        for link in path[target]["links"]:
            edges_by_indices.append((link["source"], link["target"]))
        # map index to id
        mapping = {}
        for node in path[target]["nodes"]:
            mapping[node["index"]] = node["id"]
        # transform edges from index to id
        edges_by_ids = []
        for edge in edges_by_indices:
            edges_by_ids.append((mapping[edge[0]], mapping[edge[1]]))
        self.add_edges_from(edges_by_ids)
        for node in path[target]["nodes"]:
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


    def find_best_defense(self):
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
                best_def = max(block_range_def, key=block_range_def.get)
                # debug
                print("Best Defense against Attack Step:", top_attack_step)
                print(best_def, block_range_def[best_def])
                return best_def, block_range_def[best_def]
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

