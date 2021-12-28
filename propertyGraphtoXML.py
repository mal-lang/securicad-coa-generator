from gremlin_python.process.graph_traversal import __
from gremlin_python.process.traversal import P, T
import scad
from graph_api import *


def convertPropertyGraphToSecuriCAD(g, s):
    scad.delete_all_objects_and_assocs(s)
    addObjectsToEOM(g, s)
    addAssociationsToEOM(g, s)

    scad.to_file(s, "newModelAgain.sCAD")


## Adds all objects from the property graph to the XML
def addObjectsToEOM(g, s):
    objects = g.V().hasLabel("root").out("assets").in_("instanceOf").in_("instanceOf").toList()
    counter = 1000000000
    for o in objects:
        obj = {}
        obj['id'] = str(o.id)
        obj['metaConcept'] = g.V(o.id).out("instanceOf").label().next()
        obj['name'] = g.V(o.id).values("name").next()
        obj['tag'] = g.V(o.id).valueMap().next()
        obj['exportedId'] = str(counter)

        scad.add_object(s, obj)
        counter = counter + 1

        # add active defenses
        defenses = g.V(o.id).out("defense").has('active', 1).out("instanceOf").label().toList()
        unactiveDefenses = g.V(o.id).out("defense").has('active', 0).out("instanceOf").label().toList()
        asset = g.V(o.id).out("instanceOf").label().next()
        defensList = []

        for d in defenses:
            name = d.capitalize()
            scad.set_activated_defense(s, str(o.id), name)

        # add attacksteps
    addAttackSteps(g, s)


## Adds all associations from the property graph to the XML
def addAssociationsToEOM(g, s):
    counter = -1000000000
    # assoc = {'id': counter, 'targetId': , 'sourceId': , 'targetRole': , 'sourceRole':}
    objects = g.V().hasLabel("root").out("assets").in_("instanceOf").in_("instanceOf").toList()

    for o in objects:
        assocs = g.V(o.id).match(__.as_('sourceId') \
                                 .out() \
                                 .where(__.out("instanceOf").out("instanceOf").hasLabel("assets")) \
                                 .as_("targetId")) \
            .select("sourceId", "targetId").toList()

        for a in assocs:
            # print(g.V(a["sourceId"]).properties('name').next(), g.V(a["targetId"]).properties('name').next())
            if (assocExits(s, a["sourceId"], a["targetId"])):
                continue
            else:
                # Get roles
                # print(g.V(a["targetId"].id).properties('name').next(), g.V(a["sourceId"].id).properties('name').next())
                sourceRole = getRoleInAssociation(g, a["targetId"], a["sourceId"])
                targetRole = getRoleInAssociation(g, a["sourceId"], a["targetId"])
                association = {'id': str(counter), 'targetId': str(a["targetId"].id), 'sourceId': str(a["sourceId"].id),
                               'targetRole': targetRole, 'sourceRole': sourceRole}
                scad.add_association(s, association)
                counter = counter - 1


# checks if a association exits between two objects
def assocExits(s, obj1, obj2):
    assets = scad.get_assets(s)
    for a in assets['assocs']:
        if ((a['sourceObject'] == str(obj1.id) and a['targetObject'] == str(obj2.id)) or (
                a['sourceObject'] == str(obj2.id) and a['targetObject'] == str(obj1.id))):
            # association exits
            return True
    return False


# gets all attack steps and adds them to the objects
def addAttackSteps(g, s):
    attacksteps = g.V().hasLabel("root").out("attackSteps").in_("instanceOf").project("name", "metaConcept").by(
        __.label()).by(__.in_("attackSteps").label()).toList()
    j = []
    for x in attacksteps:
        lis = [x['metaConcept'], x['name']]
        j.append(lis)

    scad.add_attacksteps(s, j)
