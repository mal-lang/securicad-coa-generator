import networkx as nx
import matplotlib.pyplot as plt


class AttackGraph(nx.DiGraph):

    def __init__(self, source = None):
        '''
        'source' is a json object created by the Session.get_attack_path_from_simulation method
        '''
        super().__init__()
        self._get_params_from_json(source)


    def _get_params_from_json(self, source = None):
        '''
        Parses 'source', which is a json object created by Session.get_attack_path_from_simulation,
        constructs the attack graph.
        '''
        if source is None:
            return
        # 1. Get rid of the "group nodes". The group nodes have a field "isGroup", with value true.
        # The remaining nodes don't have this field. :):):)
        forbiddenIndices = [node["index"]
                            for node in source["response"]["data"]["nodes"] if "isGroup" in node.keys()]
        # 2. Get rid of "missing defense" nodes, i.e., nodes representing missing objects.
        missDefIndices = [node["index"] for node in source["response"]["data"]
        ["nodes"] if node["isDefense"] and "Missing" in node["attackstep"]]
        forbiddenIndices.extend(missDefIndices)
        # the following are "edges", with the nodes being "indices".
        edges_by_indices = [(link["source"], link["target"]) for link in source["response"]["data"]
        ["links"] if (link["source"] not in forbiddenIndices and link["target"] not in forbiddenIndices)]
        # the same node might have different index in paths corresponding to different assets, so we will
        # map the indices to unique identifiers.

        # create a mapping from indices on unique identifiers. these identifiers will be nodes
        # in our attack graphs (as well as steps in CoAs). they will look like this:
        # node = "class.eid.object_name.step_name"
        # which means that node represents a step "step_name" applied to the object
        # called "object_name", with the exported id of the latter being "eid", and
        # with the object being an instance of "class".
        #
        # example: "Keystore.92.Admin Keystore.Encrypted"
        #
        # to get "object_name", need to transform slightly the "name" field from the paths returned by securiCAD.
        # the rest is as in the file.
        # 'name' fields in securiCAD's jsons look like
        #   "name": "(5) unknownService(Host-Network)"
        #   "name": "(7) UnknownAccessControl"
        mapping = {}
        for node in source["response"]["data"]["nodes"]:
            try:
                temp = node["name"]
                object_name = temp[temp.index(' ') + 1:]
            except:
                object_name = node["name"]
            gnode = node["class"] + '.' + node["eid"] + '.' + object_name + "." + node["attackstep"]

            mapping[node["index"]] = gnode
        #mapping = {node["index"]: node["name"] + "." + node["attackstep"]
         #          for node in source["response"]["data"]["nodes"]}

        # create edges with nodes indices mapped to their unique identifiers, thus no longer missinterpreting the same node as different nodes
        edges_by_uids = [(mapping[edge[0]], mapping[edge[1]]) for edge in edges_by_indices]
        self.add_edges_from(edges_by_uids)
        for node in source["response"]["data"]["nodes"]:
            if node["index"] not in forbiddenIndices:
                try:
                    temp = node["name"]
                    object_name = temp[temp.index(' ')+1:]
                except:
                    object_name = node["name"]
                gnode = node["class"] + '.' + node["eid"] + '.' + object_name + "." + node["attackstep"]
                self.nodes[gnode]["stepname"] = node["attackstep"]
                self.nodes[gnode]["frequency"] = node["frequency"]
                self.nodes[gnode]["isDefense"] = node["isDefense"]
                self.nodes[gnode]["eid"] = node["eid"]
                self.nodes[gnode]["class"] = node["class"]
                self.nodes[gnode]["ttc"] = node["ttc"]


    # def set_criticallity_scores(self, scores="fod"):
    #     '''
    #     Compute criticallity scores of counterable attack steps with respect to the metric provided.
    #     For each of the defense steps, assign to it the maximum criticality over the attack steps it counters.
    #     Score stored in self.nodes[node]['scores'].
    #
    #     scores = non-empty string of length <= 3, consisting of letters 'f', 'o' and 'd'.
    #     f = frequency, o = weighted outdegree, d = distance (will compute the inverse of distance, so that small distance
    #     results in high criticallity).
    #
    #     The order of letters in 'scores' encodes the importance ordering of the criticallity metrics.
    #     '''
    #     n = len(scores)
    #     assert n <= 3
    #     assert n > 0
    #     if "d" in scores:
    #         entryPoints = [node for node in self.nodes if self.nodes[node]["label"] == "Attacker.EntryPoint"]
    #     for node in self.nodes:
    #         if self.nodes[node]["isDefense"]:
    #             # compute parameters for each of the children, sort the children, assign the score of the most critical one to the defense
    #             children_scores = {child: [0 for i in range(len(scores))]
    #                                for child in self.successors(node)}
    #             if "f" in scores:
    #                 for child in self.successors(node):
    #                     children_scores[child][scores.index("f")] = self.nodes[child]["frequency"]
    #             if "o" in scores:
    #                 for child in self.successors(node):
    #                     children_scores[child][scores.index("o")] = sum(
    #                         [self.nodes[grandchild]["frequency"] for grandchild in self.successors(child)])
    #             if "d" in scores:
    #                 for child in self.successors(node):
    #                     try:
    #                         child_rec_distance = round(1 / min([nx.shortest_path_length(
    #                             self, source=entrypoint, target=child) for entrypoint in entryPoints]), 3)
    #                     except:
    #                         child_rec_distance = 0
    #                     children_scores[child][scores.index("d")] = child_rec_distance
    #             # get the score of the highest scored child
    #             self.nodes[node]['scores'] = get_highest_scoring(children_scores, len(scores))
    #     return

    def set_criticality_scores_of_counterable_attack_steps(self, metrics = 'fo', only_counterable = True):
        counterable_attack_steps = []
        if only_counterable:
            for node in self.nodes:
                if self.nodes[node]["isDefense"]:
                    for child in self.successors(node):
                        if child not in counterable_attack_steps:
                            counterable_attack_steps.append(child)
        else:
            counterable_attack_steps = [node for node in self.nodes if not self.nodes[node]["isDefense"]]

        if metrics == 'f':
            metrics_for_nodes = {node: [self.nodes[node]["frequency"]] for node in counterable_attack_steps}
        else:
            weighted_out_degrees = {node: [sum([self.nodes[child]["frequency"] for child in self.successors(node)])] for node in counterable_attack_steps}
            if metrics == 'o':
                metrics_for_nodes = weighted_out_degrees
            elif metrics == 'fo':
                metrics_for_nodes = {node: [self.nodes[node]["frequency"], weighted_out_degrees[node][0]] for node in counterable_attack_steps}
            else: #metrics = 'of'
                metrics_for_nodes = {node: [weighted_out_degrees[node][0], self.nodes[node]["frequency"]] for node in counterable_attack_steps}

        # sort from the node with the highest metric to the one with the lowest.
        # nodes_sorted will be a list with the first element being the node with highest metric, etc.
        if len(metrics) == 1:
            nodes_sorted = sorted(metrics_for_nodes, key=lambda key: (metrics_for_nodes[key][0]), reverse=True)
        else: #len(metrics) = 2:
            nodes_sorted = sorted(metrics_for_nodes, key=lambda key: (metrics_for_nodes[key][0], metrics_for_nodes[key][1]), reverse=True)

        # assign scores
        current_score = len(counterable_attack_steps)
        metric_of_previous_node = None
        for node in nodes_sorted:
            if metric_of_previous_node is None:
                # this is the first iteration, and score is being assigned to the most critical attack step
                self.nodes[node]["crit_score"] = current_score
            else:
                if metrics_for_nodes[node] == metric_of_previous_node:
                    # the metric of this node is the same as the previous one, so it will get the same criticality score
                    self.nodes[node]["crit_score"] = current_score
                else:
                    self.nodes[node]["crit_score"] = current_score - 1
                    current_score -= 1
            metric_of_previous_node = metrics_for_nodes[node]
        return


    def get_quality_scores_of_defense_step(self, all_prerequisites_for_w, q = 3):
        '''
        before this function is run, the function set_criticality_scores_of_counterable_attack_steps
        has to called. enough if counterable attack steps are assigned criticality scores. good coding.
        '''
        # set of attack steps countered by w and all of its prerequisites
        # print('all_prerequisites_for_w:')
        # print(all_prerequisites_for_w)
        # print("that's it")
        # print('its successors')
        # for node in all_prerequisites_for_w:
        #     for child in self.successors(node):
        #         print(child)
        # print('-----')
        assert all_prerequisites_for_w != set()
        Counter_w = set()
        for node in all_prerequisites_for_w:
            if node in self.nodes:
                countered_by_the_node = set([child for child in self.successors(node)])
                Counter_w = Counter_w.union(countered_by_the_node)
        # all_prerequisites_for_w should contain at least w.
        # so Counter_w should contain at least one attack step, and that step is a child of w.
        assert Counter_w != set()
        if q == 1:
            return len(Counter_w)
        elif q == 2:
            return sum([self.nodes[node]["crit_score"] for node in Counter_w])
        else: #q=3
            return max([self.nodes[node]["crit_score"] for node in Counter_w])


    # def def_nodes_sorted_by_scores(self, scores="fod"):
    #     '''
    #     return list of defense nodes sorted wrt their scores
    #     '''
    #     self.set_criticallity_scores(scores=scores)
    #     n = len(scores)
    #     result = {node: self.nodes[node]["scores"]
    #               for node in self.nodes if self.nodes[node]["isDefense"]}
    #     if result == {}:
    #         return []
    #
    #     # ffs
    #     print(result)
    #
    #     if n == 3:
    #         result = sorted(result, key=lambda key: (
    #             result[key][0], result[key][1], result[key][2]), reverse=True)
    #     elif n == 2:
    #         result = sorted(result, key=lambda key: (
    #             result[key][0], result[key][1]), reverse=True)
    #     else:
    #         result = sorted(result, key=lambda key: (
    #             result[key][0]), reverse=True)
    #     return list(result)


    def prettyprint(self, ttc=False):
        '''
        Not really pretty, but it displays the attack graph.
        '''
        defense_nodes = [gnode for gnode in self.nodes if self.nodes[gnode]["isDefense"]]
        cols = ["green" if i in defense_nodes else "red" for i in self.nodes]
        positioning = nx.kamada_kawai_layout(self)
        nx.draw(self, pos=positioning, with_labels=False, edge_color='silver', node_color=cols)
        if ttc:
            nx.draw_networkx_labels(G, pos=positioning, labels={
                gnode: self.nodes[gnode]["ttc"] for gnode in G.nodes}, font_size=8)
        else:
            nx.draw_networkx_labels(G, pos=positioning, labels={
                gnode: gnode for gnode in G.nodes}, font_size=8)
        plt.show()
        return


def merge_attack_graphs(graphs):
    '''
    In: list of attack graphs
    Out: an attack graph

    Given a list of attack graphs, merge them into a single graph.
    The node set and the edge set of the result are unions of the corresponding sets over graphs in A.

    Frequency of an attack step in the result is the sum of its frequencies over graphs in A.
    '''
    res = AttackGraph()
    for i in range(len(graphs)):
        graphi_frequencies_in_res = {node: res.nodes[node]["frequency"]
                                 if node in res.nodes else 0 for node in graphs[i].nodes}
        res = nx.algorithms.operators.binary.compose(res, graphs[i])
        for node in graphs[i].nodes:
            res.nodes[node]["stepname"] = graphs[i].nodes[node]["stepname"]
            res.nodes[node]["frequency"] = graphi_frequencies_in_res[node] + \
                graphs[i].nodes[node]["frequency"]
            res.nodes[node]["isDefense"] = graphs[i].nodes[node]["isDefense"]
            res.nodes[node]["eid"] = graphs[i].nodes[node]["eid"]
            res.nodes[node]["class"] = graphs[i].nodes[node]["class"]
            #res.nodes[node]["label"] = graphs[i].nodes[node]["label"]
            #res.nodes[node]["name"] = graphs[i].nodes[node]["name"]
            res.nodes[node]["ttc"] = graphs[i].nodes[node]["ttc"]
    return res


# def get_highest_scoring(d, n):
#     '''
#     In: dictionary d with values being vectors of n non-negative integer numbers, e.g.
#         d = {x: [10, 2, 0],
#              y: [0, 16, 0],
#              z: [10, 5, 3]}
#     Out: the value optimal in the reversed lexographical ordering sense.
#     Example: the above d when ordered:
#         d = {z: [10, 5, 3],
#              x: [10, 2, 0],
#              y: [0, 16, 0]},
#     so the returned object will be the list [10, 5, 3].
#     '''
#     currently_the_best = {key: d[key] for key in d}
#     for i in range(n):
#         if len(currently_the_best) == 1:
#             break
#         best_on_ith = max([d[key][i] for key in d])
#         currently_the_best = {
#             key: currently_the_best[key] for key in currently_the_best if currently_the_best[key][i] == best_on_ith}
#     # :)
#     for item in currently_the_best.values():
#         return item