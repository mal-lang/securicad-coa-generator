# Copyright 2020-2021 Wojciech Wideł <widel@kth.se>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import networkx as nx

class CoA():
    '''
    CoA is a partially ordered set, so it will be (roughly) represented as its Hasse diagram.
    '''
    def __init__(self, pre = None, hasse = None):
        # pre - dictionary, with pre[v] = list of steps that are prerequsites of v
        # to create the Hasse diagram of the poset represented with 'pre', create a directed graph from pre,
        # reverse the direction of its arcs, take the transitive reduction of the result.
        if hasse is None and isinstance(pre, dict):
            # initialize from dictionary
            self.hasse = nx.algorithms.dag.transitive_reduction(nx.DiGraph(pre).reverse())
        elif hasse is not None:
            # initialize from the provided hasse diagram
            self.hasse = hasse
        else:
            # create an empty CoA
            self.hasse = nx.DiGraph()
        self.max_elements = [node for node in self.hasse.nodes if self.hasse.out_degree(node) == 0]


    def add_from_dict(self, dict):
        '''
        Given a CoA and a dictionary of prerequisites, return new CoA arising from combining the two.
        '''
        hasse_of_dict = nx.algorithms.dag.transitive_reduction(nx.DiGraph(dict).reverse())
        # Note: taking the simple union of the hasse diagrams is sufficient,
        # since dict is expected to be a result of 'overline_pre' function defined in coagen.py.
        # In other words, if v belongs to both 'self' and 'dict', then all of its prerequisites as
        # specified by Pre relation fed to the CoAGenerator belong to both 'self' and 'dict' as well.
        hasse_of_result = nx.algorithms.operators.binary.compose(self.hasse, hasse_of_dict)
        return CoA(hasse=hasse_of_result)


    def aslist(self):
        '''
        Out: list of strings (list of defense steps)

        Turn partially order set into a list respecting precedence relation.

        Tricky! Might mess up the 'importance' order of the steps (defense added earlier to the CoA is more important
        then the ones added later).
        '''
        # if there are no precedence constraints (= no edges in the Hasse diagram of the CoA), then we preserve the importance order
        if list(self.hasse.edges) == []:
            return list(self.hasse.nodes)
        # if there are any, then we are done for :( got to maintain the precedence requirements. ROOM FOR IMPROVEMENT.
        return list(nx.topological_sort(self.hasse))


    def compute_costs_and_times(self, costs = [], times = []):
        '''
        In: lists of dictionaries, with i-th dictionary in the 'costs' list encoding
        the cost of implementation of defense steps in terms of i-th monetary resource. I.e.,
            costs[i][defense_step] = real number representing the cost of implementation
            of 'defense_step' in the context of the CoA, wrt the i-th monetary resource
        Similarly
            times[j][defense_step] = real number representing the cost of implementation
            of 'defense_step' in the context of the CoA, wrt the j-th time-like resource

        Out: list of real numbers, with the first len(costs) items representing overall monetary investments
        into execution of the CoA, and the remaining len(times) values corresponding to times.

        For potential future speed-ups: this function could be a generator, since it is used only
        for comparing costs against budgets, and there is no need for comparing as soon as one of the
        costs exceeds its corresponding budget.
        '''
        result = [self._compute_cost(cost=cost) for cost in costs]
        result.extend([self._compute_time(time=time) for time in times])
        return result


    def _compute_cost(self, cost = {}):
        return sum([cost[d] for d in self.hasse.nodes])


    def _compute_time(self, time = {}):
        return max([self._time_needed_for_a_defense(max_el, time) for max_el in self.max_elements])


    def _time_needed_for_a_defense(self, defense, time = {}):
        '''
        Compute the time needed for execution of a defense and all of its prerequisites.
        (bottom-up)

        This is a prototype. To speed computations up, store the intermediate values, so that they are not
        computed multiple times.
        '''
        if list(self.hasse.predecessors(defense)) == []:
            return time[defense]
        else:
            return time[defense] + max([self._time_needed_for_a_defense(defense=pred, time=time) for pred in self.hasse.predecessors(defense)])
