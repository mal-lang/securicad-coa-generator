from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.traversal import Cardinality, T
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
import scad
import requests
import csv
import json
import re
from os import getcwd

def drop_all(g):
    # Delete all vertices
    g.V().drop().iterate()

###########  MAL layer ##############
def mal(g):
    # Add the root asset which is a starting point for schemantic queries
    root = g.addV("root").next()
    # Add the main building blocks of MAL
    assets = g.addV("assets").next()
    attackSteps = g.addV("attackSteps").next()
    defenses = g.addV("defenses").next()
    associations = g.addV("associations").next()
    # Add root edges
    g.V(root.id).addE("attackSteps").to(attackSteps).iterate()
    g.V(root.id).addE("assets").to(assets).iterate()
    g.V(root.id).addE("defenses").to(defenses).iterate()
    g.V(root.id).addE("associations").to(associations).iterate()

    #### Add DSL and instance properties ####

    #DSL properties for attack steps
    a_type = g.addV("type").next()
    g.V(attackSteps.id).addE("DSLProperties").to(a_type).iterate()

    #Instance properties for attack steps
    ttc5 = g.addV("TTC-5%").next()
    ttc50 = g.addV("TTC-50%").next()
    ttc95 = g.addV("TTC-95%").next()

    g.V(attackSteps.id).addE("instanceProperties").to(ttc5).iterate()
    g.V(attackSteps.id).addE("instanceProperties").to(ttc50).iterate()
    g.V(attackSteps.id).addE("instanceProperties").to(ttc95).iterate()

    #DSL Porperties for associations
    role = g.addV("role").next()
    cardi_begin = g.addV("carinality_begin").next()
    g.V(associations.id).addE("DSLProperties").to(role).iterate()
    g.V(associations.id).addE("DSLProperties").to(cardi_begin).iterate()

    #Instance Properties for assets
    tag = g.addV("tag").next()
    name = g.addV("name").next()
    g.V(assets.id).addE("instanceProperties").to(tag).iterate()
    g.V(assets.id).addE("instanceProperties").to(name).iterate()

    #Instance properties for defenses
    active = g.addV("active").next()
    g.V(defenses.id).addE("instanceProperties").to(active).iterate()


def readMALSpec(url):
    # url = "https://raw.githubusercontent.com/mal-lang/coreLang/master/src/main/mal/coreLang.mal"

    # url = "https://raw.githubusercontent.com/mal-lang/coreLang/master/src/main/mal/coreLang.mal"
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


########### DSL Layer ###############

# Adds an assets in the DSL layer
def addAssets(g, assets):
    # Create all the assets
    for x in assets:
        for asset in x:
            # create the asset with the name as label
            a = g.addV(asset["name"]).next()
            rootA = g.V().hasLabel("root").out("assets").next()
            # The asset is an instance of the asset node in the MAL layer
            g.V(a.id).addE("instanceOf").to(rootA).iterate()
            # Add defenses
            addDefenses(g, a, asset["defenses"])
            # Add attack steps
            addAttackSteps(g, a, asset["attackSteps"])

    # Add functionality for extends and abtract type assets
    for x in assets:
        for asset in x:
            # check if the asset extends another asset
            if (asset['extends'] != ""):
                a = g.V().hasLabel(asset['name']).next()
                # print("a", a.id)
                extendedAsset = g.V().hasLabel(asset['extends']).next()
                # print("ea", extendedAsset.id)
                # add an extends edgen between the assets
                g.V(a.id).addE("extends").to(extendedAsset).iterate()
            # check if the asset is abstract
            if (asset['abstract']):
                g.V().hasLabel(asset['name']).property('type', 'abstract').next()


def addAssociations(g, assocs):
    for x in assocs:
        for a in x:
            role1 = a['role1'].strip("[]")
            role2 = a['role2'].strip("[]")
            # add two new assocs vertices containing information about both sides
            a1 = g.addV(a["linkName"]).property("role", role1).property("cardinality_begin", a["cardinality1"]).next()
            a2 = g.addV(a["linkName"]).property("role", role2).property("cardinality_begin", a["cardinality2"]).next()

            # add instanceOf edges to associations in the MAL Layer
            rootAs = g.V().hasLabel("root").out("associations").next()
            g.V(a1.id).addE("instanceOf").to(rootAs).iterate()
            g.V(a2.id).addE("instanceOf").to(rootAs).iterate()
            # Add association edges from the asset to its role and target edges
            g.V().hasLabel(a["asset1"]).addE("associations").to(a1).iterate()
            g.V().hasLabel(a["asset2"]).addE("associations").to(a2).iterate()

            asset2 = g.V().hasLabel(a["asset2"]).next()
            g.V(a1.id).addE("targetType").to(asset2).iterate()
            asset1 = g.V().hasLabel(a["asset1"]).next()
            g.V(a2.id).addE("targetType").to(asset1).iterate()


# Adds defenses to an asset in DSL layer
def addDefenses(g, asset, defenses):
    # g : Graph traversal source to access the database
    # asset : is a vertex in the DSL layer representing
    # the asset the defenses should relate to
    #
    # defenses : list of dictionaries {"name" : "nameOfDefense"}
    for defense in defenses:
        # Add a new vertex representing the defense
        d = g.addV(defense["name"]).next()
        # Add an edge (defense relation) from the asset having the defense
        g.V(asset.id).addE("defenses").to(d).iterate()


# Adds attack steps to an asset on the DSL layer
def addAttackSteps(g, asset, attackSteps):
    # g : Graph traversal source to access the database
    # asset : is a vertex in the DSL layer representing
    # the asset the defenses should relate to
    #
    # attackSteps : list of dictionaries {"name" : "nameOfAttackStep", "type": "type"}
    for step in attackSteps:
        a = g.addV(step["name"]).property("type", step["type"]).next()
        rootAt = g.V().hasLabel("root").out("attackSteps").next()
        g.V(a.id).addE("instanceOf").to(rootAt).iterate()
        g.V(asset.id).addE("attackSteps").to(a).iterate()


def xmlToModel(g, file, csv):
    eom = scad.open(file)
    assets = scad.get_assets(eom)
    simulation = readCSV(csv)

    for o in assets['objects']:
        if (not (o['metaConcept'] == 'Attacker')):
            # add the instance object, need to keep the securiCAD id for the associations
            vertex = g.addV().property('name', o['name']).property('id', o['id']).next()
            # Check if there is any tags present
            if ('attributesJsonString' in o):
                for k, v in json.loads(o['attributesJsonString']).items():
                    g.V(vertex.id).property(k, v).next()

            # the object vertex is an instance of a DSL asset
            metaAs = g.V().hasLabel("root").out("assets").in_("instanceOf").hasLabel(o['metaConcept']).next()
            g.V(vertex.id).addE("instanceOf").to(metaAs).iterate()

            addInstanceAttackSteps(g, vertex, o['metaConcept'], o['exportedId'], o['name'], simulation)
            addInstanceDefenses(g, vertex, o['id'], o['metaConcept'], file)

    # assumes that associations in the instance model is correct in respect to the DSL
    for a in assets['assocs']:
        if ('.attacker' not in a['targetProperty']):
            # getLinkName(g.V().has('id', a['sourceObject']), a['targetProperty'], a['sourceProperty'])
            target = g.V().has('id', a['targetObject']).next()
            g.V().has('id', a['sourceObject']).addE(a['sourceProperty']).to(target).iterate()
            source = g.V().has('id', a['sourceObject']).next()
            g.V().has('id', a['targetObject']).addE(a['targetProperty']).to(source).iterate()
    return eom


###################### Instance Layer #############################
def readCSV(file):
    # initializing the titles and rows list
    fields = []
    rows = []
    headerInfo = []

    # reading csv file
    with open(file, 'r') as csvfile:
        # creating a csv reader object
        csvreader = csv.reader(csvfile)

        # extracting field names through first row
        headerInfo.append(next(csvreader))
        headerInfo.append(next(csvreader))
        headerInfo.append(next(csvreader))
        headerInfo.append(next(csvreader))
        fields = next(csvreader)

        # extracting each data row one by one
        for row in csvreader:
            rows.append(row)

        return rows


# Add attack steps with TTC values and set active defenses
def getActiveDefenses(file, oid, metaConcept):
    assets = scad.open(file)
    # Get the meta concept
    activeDefenses = []
    for o in assets['eom_etree'].findall('objects'):
        if (o.get('id') == oid):
            for evidence in o.findall('evidenceAttributes'):
                if evidence.findall('evidenceDistribution'):
                    defense = evidence.get("metaConcept")[0].lower() + evidence.get("metaConcept")[1:]
                    # might fix to  handle probability, on, off etc
                    activeDefenses.append(defense)
    return activeDefenses


def addInstanceDefenses(g, vertex, oid, metaConcept, file):
    # get the defenses in the DSL layer associated to the object type
    defenses = g.V().hasLabel("root").out("assets").in_("instanceOf").hasLabel(metaConcept).out("defenses").project(
        "id", "label").by(T.id).by(T.label).toList()
    activeDefenses = getActiveDefenses(file, oid, metaConcept)
    for defense in defenses:
        # check if the defense is active in the oem file
        if (defense['label'] in activeDefenses):
            # create an active defense vertex
            d = g.addV().property('active', 1).next()
            # The instance object has an edge to the defense
            g.V(vertex.id).addE("defense").to(d).iterate()
            # The defense is an instance of a defence in the DSL layer
            metaD = g.V(defense['id']).next()
            g.V(d.id).addE("instanceOf").to(metaD).iterate()
        else:
            # create an inactive defense vertex
            d = g.addV().property('active', 0).next()
            # The instance object has an edge to the defense
            g.V(vertex.id).addE("defense").to(d).iterate()
            # The defense is an instance of a defence in the DSL layer
            mD = g.V(defense['id']).next()
            g.V(d.id).addE("instanceOf").to(mD).iterate()


# Gets the TTC value for an attack step, if there is none return 0
def getTTC(oid, name, attackStep, simulation):
    # TTC values is on index 6,7,8 and id of the object id is on index 1
    # and the name of the attack step is on index 5
    # print(name, attackStep)
    for row in simulation:

        if ((row[1] == oid) and (row[5].lower() == attackStep.lower())):
            return row[6], row[7], row[8]
    return 0, 0, 0


def addInstanceAttackSteps(g, vertex, metaConcept, oid, name, simulation):
    # for each attack step get the TTC values from the simulation and create the
    # attack step vertex

    # get the attack steps from the DSL layer as a list
    attackSteps = g.V().hasLabel("root").out("assets").in_("instanceOf").hasLabel(metaConcept).out(
        "attackSteps").project("id", "label").by(T.id).by(T.label).toList()
    for attackStep in attackSteps:
        TTC5, TTC50, TTC95 = getTTC(oid, name, attackStep['label'], simulation)
        # Add the attack step as a vertex in the instance layer with the ttc values
        aStep = g.addV().property('TTC-5%', TTC5).property('TTC-50%', TTC50).property('TTC-95%', TTC95).next()
        # connect to the model
        # add an edge between the object and the attack step
        g.V(vertex.id).addE("attackStep").to(aStep).next()
        # the attack step is an instance of the attack step in the DSL layer
        attackStep = g.V(attackStep['id']).next()
        g.V(aStep.id).addE("instanceOf").to(attackStep).iterate()


