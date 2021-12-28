
if __name__ == "__main__":
    metrics_for_nodes = {'(5).Access': 2, '(4).NetworkConnect': 1, '(2).AccessNetworkAndConnections': 2, '(2).FullAccess': 2,
     '(1).EntryPoint': 2}

    nodes_sorted = sorted(metrics_for_nodes, key=lambda key: (metrics_for_nodes[key]), reverse=True)
    # debug
    print("sorted nodes")
    print(nodes_sorted)

    for i in nodes_sorted:
        block_range_def = {}
        no_of_def_for_i_node = 0
        for node in self.predecessors(i):
            if self.nodes[node]["isDefense"]:
                no_of_def_for_i_node += 1
                for child in self.successors(node):
                    block_range_def[node] = sum(self.nodes[child]["frequency"])
        if no_of_def_for_i_node > 0:
            best_def = max(block_range_def, key=block_range_def.get)
            # debug
            print("best defense")
            print(best_def, block_range_def[best_def])
            return best_def, block_range_def[best_def]