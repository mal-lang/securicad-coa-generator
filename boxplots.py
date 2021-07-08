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

import matplotlib.pyplot as plt
import numpy as np
import os

'''
The functions runningTimesUkraineVSSegrid, efficienciesSegrid and runtimeWRTTargetSteps parse
the text files storing tests' results and create appropriate dictionaries.

Within the createBoxPlots function, plotBoxPlot is applied to these dictionaries to generate
boxplots. The boxplots are saved as .jpg files.
'''


def runningTimesUkraineVSSegrid(N=20):
    ''''
    the following mapping is used:

    1 = U5f
    2 = U5o
    3 = U5fo
    4 = Sf
    5 = So
    6 = Sfo
    '''
    runningTimes = {i: [] for i in range(1,7)}
    for i in range(N):
        if i < 15:
            with open('newTestsResults_Ukraine_{}.txt'.format(i)) as f:
                contents = f.readlines()
                # three blocks
                for k in range(3):
                    j = 9*k # first line of the block is line contents[j]; the last one is contents[j+6]
                    block = contents[j:j+8]
                    runtime = float(block[6].strip())
                    runningTimes[k+1].append(runtime)
        if i < 19:
            with open('TestsResults_SEGRID_{}.txt'.format(i)) as f:
                contents = f.readlines()
                # three blocks
                for k in range(3):
                    j = 8 * k  # first line of the block is line contents[j]; the last one is contents[j+6]
                    block = contents[j:j + 7]
                    runtime = float(block[5].strip())
                    runningTimes[k + 4].append(runtime)
    # relabel keys
    runningTimes['U5f'] = runningTimes.pop(1)
    runningTimes['U5o'] = runningTimes.pop(2)
    runningTimes['U5fo'] = runningTimes.pop(3)
    runningTimes['Sf'] = runningTimes.pop(4)
    runningTimes['So'] = runningTimes.pop(5)
    runningTimes['Sfo'] = runningTimes.pop(6)

    ukr_avg_median = 0
    seg_avg_median = 0
    for item in runningTimes:
        med = np.median(runningTimes[item])
        print(item, med)
        if 'U' in item:
            ukr_avg_median += med
        else:
            seg_avg_median += med
    print('avg medians:')
    print('ukraine: {}'.format(ukr_avg_median/3))
    print('segrid: {}'.format(seg_avg_median / 3))
    # for item in runningTimes:
    #     runningTimes[item].sort()
    #     median = np.median(runningTimes[item])
    #     numb_of_less_than_median = len([x for x in runningTimes[item] if x < median])
    #     print(item, median, max(runningTimes[item]), numb_of_less_than_median)
    # print('the above is about running times\n')
    return runningTimes

def efficienciesSegrid(N=19):
    '''
    1 = Sf
    2 = So
    3 = Sfo
    '''
    effs = {i: [] for i in range(1, 4)}
    for i in range(N):
        with open('TestsResults_SEGRID_{}.txt'.format(i)) as f:
            contents = f.readlines()
            # three blocks
            for k in range(3):
                j = 8 * k  # first line of the block is line contents[j]; the last one is contents[j+6]
                block = contents[j:j + 7]
                efficiency = float(block[4].strip())
                effs[k + 1].append(efficiency)
    effs['Sf'] = effs.pop(1)
    effs['So'] = effs.pop(2)
    effs['Sfo'] = effs.pop(3)
    return effs

def runtimeWRTTargetSteps():
    dirs = ['exp_U5f_{}targets'.format(i) for i in [2, 4, 6, 8]]
    numberOfTargets = {dirs[i]: 2*i+2 for i in range(4)}
    runtimesToPlot = {dir: [] for dir in dirs}
    graphSizes = {dir: [] for dir in dirs}
    for dir in dirs:
        for fileName in [f for f in os.listdir(dir) if f.endswith('.txt')]:
            # get sizes of graphs
            if fileName == 'graph_sizes.txt':
                with open(dir + '/' + fileName, 'r') as f:
                    # look for lines likes 'NUMBER OF NODES IN THE GRAPH: 88'. HEHE.
                    for line in f.readlines():
                        if 'NUMBER OF NODES IN THE GRAPH' in line:
                            graphSize = int(line.split(':')[1].strip())
                            graphSizes[dir].append(graphSize)
            else:
                # get runtimes
                with open(dir + '/' + fileName, 'r') as f:
                    runtime = round(float(f.readline().strip()), 3)
                    runtimesToPlot[dir].append(runtime)
    # rename keys
    for dir in dirs:
        runtimesToPlot[numberOfTargets[dir]] = runtimesToPlot.pop(dir)
        graphSizes[numberOfTargets[dir]] = graphSizes.pop(dir)

    return runtimesToPlot, graphSizes


def plotBoxPlot(dic, xlabel, ylabel, name, upperLabels = None):
    '''
    Taken from https://stackoverflow.com/questions/47657651/boxplot-from-dictionary-with-different-length
    and modified.

    If upperLabels is not None, then it is expected to be a dictionary with keys the same as the keys in 'dic'.
    '''
    # Python 3.5+
    labels, data = [*zip(*dic.items())]  # 'transpose' items to parallel key, value lists

    # or backwards compatible
    labels, data = dic.keys(), dic.values()

    fig, ax = plt.subplots()
    ax.boxplot(data)
    plt.xticks(range(1, len(labels) + 1), labels)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.yaxis.grid(True, linestyle='-', which='major', color='lightgrey',
                   alpha=0.5)

    if upperLabels is not None:
        ax.xaxis.grid(True, linestyle='-', which='major', color='lightgrey',
                   alpha=0.5)
        top = 2150
        numBoxes = len(dic)
        pos = np.arange(numBoxes) + 1
        upLabels = [str(upperLabels[item]) for item in upperLabels]
        for tick, label in zip(range(numBoxes), ax.get_xticklabels()):
            k = tick % 2
            ax.text(pos[tick], top + (top*0.02), upLabels[tick],
                     horizontalalignment='center', size='x-small')#, weight=weights[k])
        ax.text(2.5,top + (top*0.04),'Median graph size', horizontalalignment='center')

    plt.savefig(name+'.jpg', bbox_inches='tight', dpi=300)
    return

def createBoxPlots():
    # runtime vs target steps
    plotData, graphSizes = runtimeWRTTargetSteps()
    medians = {numberOfSteps: int(np.median(graphSizes[numberOfSteps])) for numberOfSteps in graphSizes}
    plotBoxPlot(dic=plotData, xlabel='Number of target attack steps', ylabel = 'Computation time (seconds)', name='boxplotTargetSteps', upperLabels=medians)
    #for item in plotData:
    #    print(item, 'range: {}'.format(max(plotData[item]) - min(plotData[item])))
    for item in graphSizes:
        print(item, np.median(graphSizes[item]))

    # segrid efficiencies
    segridEffs = efficienciesSegrid()
    plotBoxPlot(segridEffs, xlabel='Experiment', ylabel='Efficiency score of the result', name='boxplotEfficiencySegrid')

    # running times Ukraine vs SEGRID
    runtimes = runningTimesUkraineVSSegrid()
    plotBoxPlot(runtimes, xlabel='Experiment', ylabel='Computation time (seconds)', name='boxplotTimeUkraineVSSegrid')
    return


if __name__ == '__main__':
    createBoxPlots()
