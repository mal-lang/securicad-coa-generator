from gremlin_python.process.graph_traversal import __
from gremlin_python.process.traversal import P, T


########## Api to change the Instance layer in the data model ##########


### Structural API ###
def addNewObject(g, metaConcept, name):
    # find the meta asset
    if (not g.V().hasLabel("root").out("assets").in_("instanceOf").hasLabel(metaConcept).hasNext()):
        # The metaAsset does not exits
        print("The metaConcept: ", metaConcept, " does not exists")
        return None
    # check if the object is abstract
    if (g.V().hasLabel("root").out("assets").in_("instanceOf").hasLabel(metaConcept).has('type', 'abstract').hasNext()):
        print("The asset: ", metaConcept, " is abstract")
        return None
    metaA = g.V().hasLabel("root").out("assets").in_("instanceOf").hasLabel(metaConcept).next()
    if (metaA):
        # Get attack steps from the meta asset
        aSteps = g.V(metaA.id).out("attackSteps").toList()
        # Get defenses from the meta asset
        defenses = g.V(metaA.id).out("defenses").toList()
        # check if the asset extends another asset
        extendTree = True
        o = metaA
        while (extendTree):
            if (g.V(o.id).out("extends").hasNext()):
                # include the other assets attack steps
                extASteps = g.V(o.id).out("extends").out("attackSteps").toList()
                # include the other assets defenses
                extDefenses = g.V(o.id).out("extends").out("defenses").toList()
                # Append the lists with attack steps and defenses
                aSteps = aSteps + extASteps
                defenses = defenses + extDefenses
                # update o
                o = g.V(o.id).out("extends").next()
            else:
                extendTree = False
        # create the inctance object
        obj = g.addV().property('name', name).property('v', 1).next()
        # add edge to the meta asset
        g.V(obj.id).addE("instanceOf").to(metaA).iterate()

        # add instance attackStep (a is a graph traversal object)
        for a in aSteps:
            # create instance attack step
            step = addInstanceAttackStep(g)
            # add an instanceOf edge between the meta attack step and the instance
            g.V(step.id).addE("instanceOf").to(a).iterate()
            # add an attackStep edge from the instance object to the instance attack step
            g.V(obj.id).addE("attackStep").to(step).iterate()

        # add instance defense
        for d in defenses:
            # create the instance defense
            defense = addInstanceDefense(g)
            # add an instanceOf edge between the meta defense and the instance
            g.V(defense.id).addE("instanceOf").to(d).iterate()
            # add an defense edge from the instance object to the instance defense
            g.V(obj.id).addE("defense").to(defense).iterate()

        #

        return obj
    else:
        return []


def addNewAssociation(g, obj1, obj2, linkName, r1):
    metaConceptObj1 = g.V(obj1.id).out("instanceOf").label().next()
    metaConceptObj2 = g.V(obj2.id).out("instanceOf").label().next()
    # Make sure the objects exits
    if ((not g.V(obj1.id).hasNext()) or (not g.V(obj2.id).hasNext())):
        print("one of the object does not exits in the model")
    # Get extended assets
    hasExtended1 = True
    hasExtended2 = True
    o1 = metaConceptObj1
    o2 = metaConceptObj2
    metaExtended1 = []
    metaExtended2 = []
    while (hasExtended1):
        metaExtended1.append(o1)
        if (g.V().hasLabel(o1).out("extends").hasNext()):
            o1 = g.V().hasLabel(o1).out("extends").label().next()
        else:
            hasExtended1 = False

    while (hasExtended2):
        metaExtended2.append(o2)
        if (g.V().hasLabel(o2).out("extends").hasNext()):
            o2 = g.V().hasLabel(o2).out("extends").label().next()
        else:
            hasExtended2 = False
    # r1 needs to be provided
    # eqObjects = False
    # if(metaConceptObj1 == metaConceptObj2):
    #     eqObjects = True

    foundAnAssoc = False
    inheritedFrom1 = ""
    inheritedFrom2 = ""
    assocs = []
    for asset1 in metaExtended1:
        if (assocs):
            break
        for asset2 in metaExtended2:
            if (not foundAnAssoc):
                assocs = g.V().hasLabel("root").out("associations").in_("instanceOf").hasLabel(linkName). \
                    where(__.or_(__.and_( \
                    __.in_("associations").hasLabel(asset1), \
                    __.out("targetType").hasLabel(asset2)) \
                    , \
                    __.and_( \
                        __.in_("associations").hasLabel(asset2), \
                        __.out("targetType").hasLabel(asset1)))).toList()
                if (assocs):
                    foundAnAssoc = True
                    inheritedFrom1 = asset1
                    inheritedFrom2 = asset2
                    break

    # check that both metaConcepts are a member of the link
    print("assocs", assocs)
    if (not foundAnAssoc):
        print("The associations does not exits")
        return False
    valid = True
    for asset in assocs:
        target = g.V(asset.id).out("targetType").label().next()
        start = g.V(asset.id).in_("associations").label().next()
        if not ((target == inheritedFrom1 or start == inheritedFrom1) and (
                target == inheritedFrom2 or start == inheritedFrom2)):
            print("The association does not exits")
            valid = False
    print("is it valid in addnewassoc? ", valid)
    if (valid):
        roleAndCardObj1 = g.V().hasLabel(inheritedFrom1).out("associations").hasLabel(linkName).has('role', r1).project(
            "role", "card").by("role").by("cardinality_begin").next()
        roleAndCardObj2 = g.V().hasLabel(inheritedFrom2).out("associations").hasLabel(linkName).not_(
            __.has('role', r1)).project("role", "card").by("role").by("cardinality_begin").next()
        # else:
        #     roleAndCardObj1 = g.V(obj1.id).out("instanceOf").out("associations").hasLabel(linkName).project("role", "card").by("role").by("cardinality_begin").next()
        #     roleAndCardObj2 = g.V(obj2.id).out("instanceOf").out("associations").hasLabel(linkName).project("role", "card").by("role").by("cardinality_begin").next()
        #     #Add edges named after the roles (with a v = 1 to indacate a new change)
        #     #check that the assoc does not already exists
        if (g.V(obj1.id).out(roleAndCardObj2["role"]).hasId(obj2.id).hasNext()):
            # Already exits
            print("Trying to add an exitsting association between two objects")
            return False
        o2 = g.V(obj2.id).next()
        o1 = g.V(obj1.id).next()
        g.V(obj1.id).addE(roleAndCardObj2["role"]).property('v', 1).to(o2).iterate()
        g.V(obj2.id).addE(roleAndCardObj1["role"]).property('v', 1).to(o1).iterate()
    return valid


# Removing an object means that all edges connected to that object will be removed
def removeObject(g, obj):
    # Make sure that the object exits
    if (not g.V(obj.id).hasNext()):
        print("Tried to remove an non-existing object")
        return
        # make sure that it is an instance of an attack step
    if (not g.V(obj.id).out("instanceOf").out("instanceOf").hasLabel("assets").hasNext()):
        print("Trying to remove something that is not an instance of an asset in the DSL layer")
        return
    # Set the object to 0
    g.V(obj.id).property('v', 0).next()
    # Set all edges from the object 0
    if (g.V(obj.id).bothE().where(__.otherV().out("instanceOf").out("instanceOf").hasLabel("assets")).hasNext()):
        g.V(obj.id).bothE().where(__.otherV().out("instanceOf").out("instanceOf").hasLabel("assets")).property('v',
                                                                                                               0).next()


# The role of obj2 is needed obj -> obj2
def removeAssociation(g, obj1, obj2, role2):
    # check that the obejcts exits
    if (not (g.V(obj1.id).hasNext() or g.V(obj2.id).hasNext())):
        print("One of the objects in the removeAssociation call does not exits")
        return
    # Check that the association exits
    if (not g.V(obj1.id).out(role2).hasId(obj2.id).hasNext()):
        # does not exits
        print("trying to removed an non-exitsting association")
        return
    # Find the role in the oposite direction
    # Get the link name, needs to be fixed with inheritance
    # link = getLinkName(g, obj1, obj2, role2)
    # Maybe change
    role1 = g.V(obj2.id).outE().where(__.inV().hasId(obj1.id)).label().next()
    # role1 = g.V(obj1.id).out("instanceOf").out("associations")\
    #             .where(__.and_(__.hasLabel(link),\
    #                           __.out("targetType").hasLabel(g.V(obj2.id).out("instanceOf").label().next()))\
    #             ).values("role")\
    #             .next()

    # tag the edges with 0
    g.V(obj1.id).outE(role2).where(__.inV().hasId(obj2.id)).property('v', 0).next()
    g.V(obj2.id).outE(role1).where(__.inV().hasId(obj1.id)).property('v', 0).next()


### Validation on structural changes ###
## The model is assumed to be correct outside the pattern
# Validations on new object menas validating that object and its neigbouring objects
# since the carinalities for thos can be affected
# VALIDATION on new assocs validates the objects connecting through the assoc
# all validations does not take account for 0:s
def validatePatternExchange(g):
    # Need to look for 1:s (added objects and assocs)
    # Validate the cardinalites, of that object and its neigbouring objects
    # that is not taged with a 0
    newObejcts = g.V().has('v', 1).toList()  # Need a full validation
    newAssocs = g.E().has('v', 1).toList()  # Validate only that assoc for the objects
    removedAssocs = g.E().has('v', 0).toList()  # Validate only that assoc for the objects
    valid = True
    # Validate all new objects
    for obj in newObejcts:
        if (valid):
            valid = fullValidateObject(g, obj)  # Validate the newly added object

    print("1", valid)
    # Validate new assocs
    for assoc in newAssocs:
        if (valid):
            valid = validateAssoc(g, assoc)
    print("2", valid)
    # Validate removed assocs (same check as for new assocs)
    for rAssoc in removedAssocs:
        if (valid):
            valid = validateAssoc(g, rAssoc)
    print("3", valid)
    # If the pattern exchange is valid remove the 0:s from the model and keep the 1:s
    if (valid):
        print("change")
        for rAssoc in removedAssocs:
            g.E(rAssoc.id).drop().iterate()
        # permanently remove object with 0:s
        removedObjects = g.V().has('v', 0).toList()
        for o in removedObjects:
            deleteObject(g, o)

        # Drop all the properties with 1:s
        g.V().has('v', 1).properties('v').drop().iterate()
        g.E().has('v', 1).properties('v').drop().iterate()

        return True

    else:  # Keep the 0:s and remove the 1:s
        print("restore")
        for assoc in newAssocs:
            g.E(assoc.id).drop().iterate()
        for o in newObejcts:
            deleteObject(g, o)

        # Drop all the properties with 0:s
        g.V().has('v', 0).properties('v').drop().iterate()
        g.E().has('v', 0).properties('v').drop().iterate()

        return False


def deleteObject(g, o):
    # delete all attackSteps and defenses
    g.V(o.id).out("defense").drop().iterate()
    g.V(o.id).out("attackStep").drop().iterate()

    # delete the object
    g.V(o.id).drop().iterate()


def validateAssoc(g, assoc):
    objToValidate = g.E(assoc.id).outV().next()
    print("-----ValidateAssoc---------")
    print("objToValidate", g.V(objToValidate.id).properties("name").toList())
    meta1 = g.E(assoc.id).outV().out("instanceOf").label().next()
    meta2 = g.E(assoc.id).inV().out("instanceOf").label().next()
    meta1Extensions = [meta1]
    meta2Extensions = [meta2]
    meta1Extensions = meta1Extensions + getExtensionsions(g, meta1)
    print("meta1", meta1)
    print("extensions", meta1Extensions)
    meta2Extensions = meta2Extensions + getExtensionsions(g, meta2)
    print("meta2", meta2)
    print("extensions", meta2Extensions)
    role = g.E(assoc.id).label().next()

    card = getCardinalityForAssoc(g, meta1, meta2, role)

    # card = g.E(assoc.id).\
    #         inV().\
    #         out("instanceOf").\
    #         out("associations").\
    #         has('role', role).\
    #         where(__.out("targetType").hasLabel(meta1)).\
    #         valueMap().next()
    # validate the assoc for meta 1

    # Works for original meta
    # if(card):
    #     if(validateOneAssocForObject(g, objToValidate, meta2, role, card['cardinality_begin'][0])):
    #         return True
    # else:
    for e1 in meta1Extensions:
        for e2 in meta2Extensions:
            card = getCardinalityForAssoc(g, e1, e2, role)
            if (card):
                if (validateOneAssocForObject(g, objToValidate, e2, role, card['cardinality_begin'][0])):
                    return True
    return False

    # return validateOneAssocForObject(g, objToValidate, meta2, role, card['cardinality_begin'][0])


def getCardinalityForAssoc(g, meta1, meta2, role):
    if (not g.V().hasLabel(meta2).out("associations").has('role', role).hasNext()):
        return []
    if (not g.V().hasLabel(meta2).out("associations").has('role', role).where(
            __.out("targetType").hasLabel(meta1)).hasNext()):
        return []
    card = g.V(). \
        hasLabel(meta2). \
        out("associations"). \
        has('role', role). \
        where(__.out("targetType").hasLabel(meta1)). \
        valueMap().next()
    return card


def getExtensionsions(g, metaC):
    extends = []
    meta = metaC
    hasExtends = True
    while (hasExtends):
        if (g.V().hasLabel(meta).out("extends").hasNext()):
            meta = g.V().hasLabel(meta).out("extends").label().next()
            extends.append(meta)
        else:
            hasExtends = False
    return extends


## Needs remake, mabe create a function that for every extends do the same
def fullValidateObject(g, o):
    metaAsset = getMetaConcept(g, o)
    if (metaAsset):
        associations = g.V().hasLabel(metaAsset) \
            .match(__.as_("metaStart").in_("targetType").as_("assocInfo"), \
                   __.as_("assocInfo").in_("associations").as_("metaTarget")). \
            select("assocInfo", "metaTarget").by(__.valueMap()).by(__.label()).toList()
        # print("###### Meta Extensions #####")
        # print(associations)

        # print("##### EXTENSTION ######")

        extends = getExtensionsions(g, metaAsset)
        # print("extends", extends)
        extendedAssocs = []
        if (extends):
            for e in extends:
                x = g.V().hasLabel(e) \
                    .match(__.as_("metaStart").in_("targetType").as_("assocInfo"), \
                           __.as_("assocInfo").in_("associations").as_("metaTarget")). \
                    select("assocInfo", "metaTarget").by(__.valueMap()).by(__.label()).toList()
                extendedAssocs = extendedAssocs + x
            # print("extendesAssocs", extendedAssocs)
        # Get all the assocs out of the object in the language (DSL layer)
        valid = True
        # metaAssocs = g.V(o.id).\
        #             match(__.as_("start").out("instanceOf").as_("metaStart"),\
        #                 __.as_("metaStart").in_("targetType").as_("assocInfo"),\
        #                 __.as_("assocInfo").in_("associations").as_("metaTarget")).\
        #             select("assocInfo", "metaTarget").by(__.valueMap()).by(__.label()).toList()
        for assoc in associations:
            if (valid):
                valid = validateOneAssocForObject(g, o, assoc['metaTarget'], assoc['assocInfo']['role'][0],
                                                  assoc['assocInfo']['cardinality_begin'][0])
            else:
                return False
        for k in extendedAssocs:
            if (valid):
                valid = validateOneAssocForObject(g, o, assoc['metaTarget'], assoc['assocInfo']['role'][0],
                                                  assoc['assocInfo']['cardinality_begin'][0])
            else:
                return False
        return valid
    # Not a valid object
    else:
        return False


def validateOneAssocForObject(g, o, targetMeta, role, card):
    # print(card)
    cardinality = card.split("..")

    # Set the upper and lowe bound for cardinalities
    if (len(cardinality) > 1):
        lowerBound = cardinality[0]
        upperBound = cardinality[1]
    else:
        lowerBound = cardinality[0]
        upperBound = True

    if (upperBound == "*"):
        upperBound = -1  # -1 = inf or *
    if (lowerBound == "*"):
        lowerBound = -1
        # print("--", role, "--", lowerBound, "-meta-",targetMeta, "--", upperBound)
    # count go to all the objects connected through the role
    nrOfConnections = g.V(o.id).outE(role). \
        not_(__.has('v', 0)). \
        where(__.and_(__.inV().out("instanceOf").hasLabel(targetMeta), \
                      __.not_(__.inV().has('v', 0)))). \
        inV().count().next()

    # count the connections to the object matching the current association (without 0:s)
    # a fixed cardinlaity
    if (upperBound == True):
        if (nrOfConnections == int(lowerBound) or lowerBound == -1):
            # Valid
            return True

        else:
            # not valid
            print("1")
            return False

    # lower and upper bound
    else:
        if (upperBound == -1):
            # do not need to think about the max
            if (nrOfConnections >= int(lowerBound)):
                return True
            else:
                print("2")
                return False
        else:
            # need to be in the intervall between begin and end
            if ((nrOfConnections >= int(lowerBound)) and (nrOfConnections <= int(upperBound))):
                return True
            else:
                print("3")
                return False


# creates a new attack step vertex in the instance layer.
# Adds 0 as a default value to new attack steps
def addInstanceAttackStep(g):
    return g.addV().property("TTC-5%", 0).property("TTC-50%", 0).property("TTC-95%", 0).next()


# creates a new defense vertex in the instance layer
# the default values is 0 for the active property
def addInstanceDefense(g):
    return g.addV().property("active", 0).next()


#### API to change properties ####

# Activate a defense if it exits
def activateDefense(g, obj, defense):
    # g: graph traversal source
    # obj: the object that should have the defense active
    # defense: the name of the defense to activate
    g.V(obj.id).out("defense").where(__.out("instanceOf").hasLabel(defense)).property("active", 1).next()


# deactivate a defense if it exits
def deactivateDefense(g, obj, defense):
    # g: graph traversal source
    # obj: the object that should have the defense deactivated
    # defense: the name of the defense to deactivate
    g.V(obj.id).out("defense").where(__.out("instanceOf").hasLabel(defense)).property("active", 0).next()


# adds a tag key value pair as a property to an object
def addTag(g, obj, tag):
    # g: graph traversal source
    # obj: the vertex that should include the tag
    # tag: {key, val}
    for k, v in tag.items():
        g.V(obj.id).property(k, v).next()


# Removes a tag from the objects
def removeTag(g, obj, tag):
    # g: graph traversal source
    # obj: the vertex that the tag should be removed from
    # tag: {key, val}
    for k, v in tag.items():
        g.V(obj.id).properties(k).drop()


# Sets the TTC values to an attack step to an instance in the model
def setTTC(g, obj, attackStep, ttc):
    # g graph traversal source
    # obj the vertex that has the attack step
    # attackStep the name of the attack step
    # ttc {'TTC-5%' : value, 'TTC-50%': value, 'TTC-95%' : value}
    g.V(obj.id).out("attackStep"). \
        where(__.out("instanceOf").hasLabel(attackStep)). \
        property("TTC-5%", ttc["TTC-5%"]). \
        property("TTC-50%", ttc["TTC-50%"]). \
        property("TTC-95%", ttc["TTC-95%"]).next()


#### Functions to retrive information ####

# Get the name of the association between two objects
def getLinkName(g, obj1, obj2, role2):
    # g : graph traversal source
    # obj1: reference to one of the objects in the association
    # obj2: reference to the othe object in the association
    # role2: the role of obj2 in the association
    # returns : the name of the association as a String

    # Remake to support extends
    meta1 = g.V(obj1.id).out("instanceOf").label().next()
    meta2 = g.V(obj2.id).out("instanceOf").label().next()
    o1E = [meta1] + getExtensionsions(g, meta1)
    o2E = [meta2] + getExtensionsions(g, meta2)
    linkName = ""
    hasLink = False
    for e1 in o1E:
        if (hasLink):
            break
        for e2 in o2E:
            if (not hasLink):
                if (g.V().hasLabel(e2).out("associations").where(
                        __.and_(__.has("role", role2), __.out("targetType").hasLabel(e1))).hasNext()):
                    linkName = g.V().hasLabel(e2).out("associations") \
                        .where(__.and_(__.has("role", role2), \
                                       __.out("targetType").hasLabel(e1)) \
                               ) \
                        .label() \
                        .next()
                    hasLink = True
            else:
                break

    # linkName = g.V(obj2.id).out("instanceOf").out("associations")\
    #     .where(__.and_(__.has("role", role2),\
    #                    __.out("targetType").hasLabel(g.V(obj1.id).out("instanceOf").label().next()))\
    #         )\
    #     .label()\
    #     .next()
    return linkName


# get the role of obj 2
def getRoleInAssociation(g, obj1, obj2):
    # g : graph traversal source
    # obj1 : One of the objects in the association
    # obj2 : The other object in the association
    # returns : the role of obj2 in the association as a string
    role = g.V(obj1.id).outE().where(__.inV().hasId(obj2.id)).label().next()
    return role


# gets the asset of wich the object is an instance of
def getMetaConcept(g, obj):
    # g : graph traversal source
    # obj : A reference to the object
    # returns : the asset of which obj is an instance of as a String
    # The object is actually an instance of an asset in the model
    if (g.V(obj.id).out("instanceOf").out("instanceOf").hasLabel("assets").hasNext()):
        return g.V(obj.id).out("instanceOf").label().next()
    # not an instance of an asset in the DSL layer
    else:
        print("The object provided is not an instance of an asset in the DSL layer")
        return None



