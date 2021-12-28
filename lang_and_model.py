from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.traversal import Cardinality, T
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
import scad
import requests
import csv
import json
import re
from os import getcwd

def readLang(url):

    directory = getcwd()
    filename = 'mal.txt'
    r = requests.get(url)
    f = open(filename, 'w')
    f.write(r.text)
    f.close()

    with open(filename) as infile, open('output.txt', 'w') as outfile:
        for line in infile:
            if not line.strip(): continue  # skip the empty line
            outfile.write(line)  # non-empty line. Write it to output

    spec = open('output.txt', "r")
    content = spec.readlines()
    asso = False
    assocs = []
    assets = []
    currentAsset = {"name": "", "attackSteps": [], "defenses": [], "extends": "", "abstract": False}

    for line in content:
        words = line.split()
        if (asso == False):
            if (len(words) >= 2):
                if (words[0] == "asset"):
                    if (currentAsset["name"] != ""):
                        assets.append(currentAsset)
                        # the asset extends another asset
                    if (len(words) >= 4 and words[2] == "extends"):
                        currentAsset = {"name": "", "attackSteps": [], "defenses": [], "extends": "", "abstract": False}
                        currentAsset["name"] = words[1]
                        print(words[1], " extends ", words[3])
                        currentAsset['extends'] = words[3]
                    else:
                        currentAsset = {"name": "", "attackSteps": [], "defenses": [], "extends": "", "abstract": False}
                        currentAsset["name"] = words[1]

                    ## Create a new asset
                if (words[1] == "asset"):
                    if (currentAsset["name"] != ""):
                        assets.append(currentAsset)
                        currentAsset = {"name": "", "attackSteps": [], "defenses": [], "extends": "", "abstract": False}

                    currentAsset["name"] = words[2]

                    if (words[0] == "abstract"):
                        print("asset ", words[2], " is abstract")
                        currentAsset["abstract"] = True

                # All defenses and attack steps until a new asset is
                # present belongs to the prev asset
                # Needs more functionality for E, !E, @hidden etc..

                if (words[0] == "|"):  # Attack step of type OR
                    currentAsset["attackSteps"].append({"name": words[1], "type": "OR"})
                if (words[0] == "&"):  # Attack step of type AND
                    currentAsset["attackSteps"].append({"name": words[1], "type": "AND"})
                if (words[0] == "#"):  # Defense
                    currentAsset["defenses"].append({"name": words[1]})
                # spec.close()

                ## no more assets, just associations
                if (words[0] == "associations"):
                    asso = True
                    assets.append(currentAsset)

        else:
            if (len(words) >= 2):
                for d in assets:

                    if (d["name"] == words[0]):
                        line = ''.join(words)
                        lineContent = re.split('\[|\]|<--|-->', line)
                        # print(lineContent)

                        assoc = {}

                        assoc["linkName"] = lineContent[3]
                        assoc["asset1"] = lineContent[0]
                        assoc["asset2"] = lineContent[6]
                        assoc["role1"] = lineContent[1]
                        assoc["role2"] = lineContent[5]
                        assoc["cardinality1"] = lineContent[2]
                        assoc["cardinality2"] = lineContent[4]
                        assocs.append(assoc)
                        break
    if (asso == False):
        assets.append(currentAsset)

    return assets, assocs

