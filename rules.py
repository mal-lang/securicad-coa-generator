from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.graph_traversal import __
from gremlin_python.process.traversal import Cardinality, T
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
import matplotlib.pyplot as plt
import networkx as nx
from graph_api import *


def drawInstanceLevel(g):
    # all edges between two objects
    e = g.E().where(__.and_(__.inV().out("instanceOf").out("instanceOf").hasLabel("assets"), \
                            __.outV().out("instanceOf").out("instanceOf").hasLabel("assets"))).toList()
    edges = []
    for edge in e:
        elem = {}
        elem['role'] = g.E(edge.id).label().next()
        fr = g.E(edge.id).outV().project("name", "id").by(__.values("name")).by(__.id()).toList()
        to = g.E(edge.id).inV().project("name", "id").by(__.values("name")).by(__.id()).toList()
        elem['from'] = fr[0]['name']  # + str(fr[0]['id'])
        elem['to'] = to[0]['name']  # + str(to[0]['id'])
        edges.append(elem)

    k = []
    for i in edges:
        h = [i['from'], i['to']]
        k.append(h)

    G = nx.MultiDiGraph()
    G.add_edges_from(k)
    pos = nx.circular_layout(G)
    plt.figure()
    nx.draw(G, pos, connectionstyle='arc3, rad = 0.1', edge_color='black', width=1, linewidths=1, \
            node_size=800, node_color='pink', alpha=0.9, \
            labels={node: node for node in G.nodes()})
    nx.draw_networkx_edge_labels(G, pos, label_pos=0.3,
                                 edge_labels={(elem['from'], elem['to']): elem['role'] for elem in edges},
                                 font_color='red')
    plt.axis('off')
    plt.show()


def example1(g):
    # Get all objects in the instance layer
    obj = g.V().hasLabel("root").out("assets").in_("instanceOf").in_("instanceOf").project("name", "id").by(
        __.properties("name")).by(__.id()).toList()
    print("The objects in the model: ", obj)


# Filter Exchange Patterns
def missingAssoc(g):
    ### ANTI-PATTERN ###
    antiPattern = g.V() \
        .match( \
        __.as_("apps") \
            .where( \
            __.out("instanceOf") \
                .hasLabel("Application")), \
 \
        __.as_("apps") \
            .where( \
            __.not_( \
                __.out() \
                    .out("instanceOf") \
                    .hasLabel("Application")))) \
        .select("apps").toList()

    ### REWRITE PATTERN ###
    for p in antiPattern:
        # STRUCTURAL CHANGES
        o = addNewObject(g, "Application", "newApp")
        addNewAssociation(g, p, o, "AppExecution", "hostApp")
        # VALIDATE CHANGES
        validatePatternExchange(g)
        # CHANGE PROPERTIES
        addTag(g, o, {"IDS": "ids"})


def unwantedObject(g):
    ### ANTI-PATTERN ###
    antiPattern = g.V().match( \
        __.as_("id").where( \
            __.out("instanceOf") \
                .hasLabel("Identity")), \
 \
        __.as_("id").where( \
            __.not_( \
                __.out() \
                    .out("instanceOf"). \
                    hasLabel("Data"))), \
 \
        __.as_("id").where( \
            __.out("defense") \
                .where( \
                __.and_( \
                    __.out("instanceOf") \
                        .hasLabel("twoFactorAuthentication"), \
 \
                    __.has('active', 0) \
                    )) \
            )) \
        .select("id").toList()

    ### REWRITE PATTERN ###
    for p in antiPattern:
        # STRUCTURAL CHANGES
        removeObject(g, p)
        # VALIDATE CHANGES
        validatePatternExchange(g)
        # CHANGE PROPERTIES


def needForDefense(g):
    ### BAD PATTERN ###
    bp = g.V().match( \
        __.as_("id"). \
            where( \
            __.out("instanceOf") \
                .hasLabel("Identity")), \
 \
        __.as_("id"). \
            where( \
            __.out("defense") \
                .where( \
                __.and_( \
                    __.out("instanceOf"). \
                        hasLabel("TwoFactorAuthentication"), \
 \
                    __.has("active", 0)))), \
 \
        __.as_("id"). \
            where( \
            or_( \
                __.out("writePrivData") \
                    .out("instanceOf") \
                    .hasLabel("Application"), \
 \
                __.out("deletePrivData") \
                    .out("instanceOf") \
                    .hasLabel("Application"))) \
        ) \
        .select("id").toList()

    ### REWRITE PATTERN ###
    for p in bp:
        # STRUCTURAL CHANGES

        # VALIDATE CHANGES

        # CHANGE PROPERTIES
        activateDefense(g, p, "twoFactorAuthentication")


def removeUnwantedObject(g):
    ### BAD PATTERN ###
    bp = g.V().match( \
        __.as_("data") \
            .where( \
            __.out("instanceOf").hasLabel("Data")), \
 \
        __.as_("data") \
            .where( \
            __.out().out("instanceOf").hasLabel("Identity")), \
 \
        __.as_("data") \
            .where( \
            __.out().out("instanceOf").hasLabel("Credentials"))) \
        .select("data").toList()

    ### REWRITE PATTERN ###
    for p in bp:
        # STRUCTURAL CHANGES
        removeObject(g, p)
        # VALIDATE CHANGES
        validatePatternExchange(g)
        # CHANGE PROPERTIES


def duplicateObject(g):
    ### BAD PATTERN ###
    antiPattern = g.V().match( \
        __.as_("data") \
            .where( \
            __.out("instanceOf") \
                .hasLabel("Data")), \
 \
        __.as_("data") \
            .where( \
            __.out() \
                .out("instanceOf") \
                .hasLabel("Identity")), \
 \
        __.as_("data") \
            .where( \
            __.out() \
                .out("instanceOf") \
                .hasLabel("Credentials")), \
 \
        __.as_("data") \
            .out() \
            .where( \
            __.out("instanceOf") \
                .hasLabel("Identity")) \
            .fold() \
            .as_("ids"), \
 \
        __.as_("data") \
            .out() \
            .where( \
            __.out("instanceOf") \
                .hasLabel("Credentials")) \
            .fold() \
            .as_("creds") \
        ) \
        .select("data", "ids", "creds").toList()

    ### REWRITE PATTERN ###
    for p in antiPattern:
        # STRUCTURAL CHANGES
        removeObject(g, p['data'])
        o = addNewObject(g, "Data", "NewData")
        # add same associations to the new object
        for i in p['ids']:
            print("ids : ")
            print(g.V(i.id).properties('name').next())
            role2 = getRoleInAssociation(g, p['data'], i)
            linkName = getLinkName(g, p['data'], i, role2)
            addNewAssociation(g, i, o, linkName)
        for j in p['creds']:
            print("creds: ")
            print(g.V(j.id).properties('name').next())
            role2 = getRoleInAssociation(g, p['data'], j)
            linkName = getLinkName(g, p['data'], j, role2)
            addNewAssociation(g, j, o, linkName)
        # VALIDATE CHANGES
        validatePatternExchange(g)
        # CHANGE PROPERTIES


###### Structural Exchange Patterns ######
def twoObjects(g):
    bp = g.V().match( \
        __.as_("app") \
            .where( \
            __.out("instanceOf") \
                .hasLabel("Credentials")), \
 \
        )
    return


def updateInBetween(g):
    ### BAD PATTERN ###
    bp = g.V().match( \
        __.as_("cred") \
            .where( \
            __.out("instanceOf") \
                .hasLabel("Credentials")), \
 \
        __.as_("cred") \
            .out("identities") \
            .where(__.out("instanceOf") \
                   .hasLabel("Identity")) \
            .as_("id"), \
 \
        __.not_( \
            __.as_("cred") \
                .out() \
                .where( \
                __.out("instanceOf") \
                    .hasLabel("Data") \
                    .out() \
                    .as_("id") \
                ))) \
        .select("cred", "id").toList()
    print(bp)
    ### REWRITE PATTERN ###
    for p in bp:
        # STRUCTURAL CHANGES
        removeAssociation(g, p['cred'], p['id'], "identities")
        data = addNewObject(g, "Data", "data")
        addNewAssociation(g, p['cred'], data, "EncryptionCredentials")
        addNewAssociation(g, data, p['id'], "ReadPrivileges")
        # VALIDATE CHANGES
        success = validatePatternExchange(g)
        # CHANGE PROPERTIES
        if (success):
            activateDefense(g, data, "authenticated")


def twoConnectedWithFilters(g):
    ### ANTI-PATTERN ###
    antiPattern = g.V().match( \
        __.as_("app") \
            .where( \
            __.out("instanceOf") \
                .hasLabel("Application")), \
 \
        __.as_("id") \
            .where( \
            __.out("instanceOf") \
                .hasLabel("Identity")), \
 \
        __.as_("app") \
            .out() \
            .as_("id"), \
 \
        __.as_("app") \
            .where( \
            __.out("defense") \
                .where( \
                __.and_( \
                    __.out("instanceOf"). \
                        hasLabel("disabled"), \
 \
                    __.has("active", 0)))), \
 \
        __.as_("id") \
            .where( \
            __.out() \
                .where( \
                __.out("instanceOf") \
                    .hasLabel("Application") \
                ) \
                .count() \
                .is_(P.gte(2)) \
            ), \
 \
        __.as_("app") \
            .where( \
            __.out() \
                .out("instanceOf") \
                .hasLabel("System") \
            )) \
        .select("app", "id").toList()

    ### REWRITE PATTERN ###
    for p in antiPattern:
        # STRUCTURAL CHANGES
        o = addNewObject(g, "System", "newSystem")
        addNewAssociation(g, p["app"], o, "SysExecution")

        # VALIDATE CHANGES
        success = validatePatternExchange(g)
        # CHANGE PROPERTIES


def threeConnectedInARow(g):
    ### BAD PATTERN ###
    antiPattern = g.V().match( \
        __.as_("nw") \
            .where( \
            __.out("instanceOf") \
                .hasLabel("Network")), \
 \
        __.as_("fw") \
            .where( \
            __.out("instanceOf") \
                .hasLabel("RoutingFirewall")), \
 \
        __.as_("system") \
            .where( \
            __.out("instanceOf") \
                .hasLabel("System")), \
 \
        __.as_("nw") \
            .out() \
            .as_("fw"),

        __.as_("fw") \
            .out() \
            .as_("system"), \
 \
        __.as_("nw") \
            .where( \
            __.not_( \
                __.out \
                    .out("instanceOf") \
                    .hasLabel("Application")))) \
        .select('nw', 'fw', 'system') \
        .toList()

    ### REWRITE PATTERN ###
    for p in antiPattern:
        # STRUCTURAL CHANGES
        o = addNewObject(g, "Application", "newApp")
        addNewAssociation(g, p['nw'], o, "NetworkExposure")
        addNewAssociation(g, p['system'], o, "SysExecution")
        # VALIDATE CHANGES
        success = validatePatternExchange(g)
        # CHANGE PROPERTIES


def twoOfSameKind(g):
    antiPattern = g.V().match( \
        )

    ### REWRITE PATTERN ###
    for p in antiPattern:
        # STRUCTURAL CHANGES
        o = addNewObject(g, "Application", "newApp")
        addNewAssociation(g, p['nw'], o, "NetworkExposure")
        addNewAssociation(g, p['system'], o, "SysExecution")
        # VALIDATE CHANGES
        success = validatePatternExchange(g)
        # CHANGE PROPERTIES


##### Complex Exchange PAtterns #####
def smalLoop(g):
    bp = g.V().match( \
        __.as_("system") \
            .where( \
            __.out("instanceOf") \
                .hasLabel("System")), \
 \
        __.as_("app") \
            .where( \
            __.out("instanceOf") \
                .hasLabel("Application")), \
 \
        __.as_("id") \
            .where( \
            __.out("instanceOf") \
                .hasLabel("Identity")), \
 \
        __.as_("system") \
            .out() \
            .as_("app"), \
 \
        __.as_("app") \
            .out() \
            .as_("id"), \
 \
        __.as_("system") \
            .out() \
            .as_("id"), \
        )


# def bigLoop(g):

def star(g):
    bp = g.V().match( \
        __.as_("system") \
            .where( \
            __.out("instanceOf") \
                .hasLabel("System")), \
 \
        __.as_("data") \
            .where( \
            __.out("instanceOf") \
                .hasLabel("Data")), \
 \
        __.as_("firewall") \
            .where( \
            __.out("instanceOf") \
                .hasLabel("RoutingFirewall")), \
 \
        __.as_("id") \
            .where( \
            __.out("instanceOf") \
                .hasLabel("Identity")), \
 \
        __.as_("app") \
            .where( \
            __.out("instanceOf") \
                .hasLabel("Application")), \
 \
        __.as_("system") \
            .out() \
            .as_("id"), \
 \
        __.as_("system") \
            .out() \
            .as_("data"), \
 \
        __.as_("system") \
            .out() \
            .as_("firewall"), \
 \
        __.as_("system") \
            .out() \
            .as_("app") \
        ) \
        .select("system", "data", "firewall", "id", "app") \
        .toList()
    ### REWRITE PATTERN ###
    for p in bp:
        # STRUCTURAL CHANGES
        # Should not work
        obj = addNewObject(g, "Data", "newData")
        addNewAssociation(g, p['system'], obj, "DataHosting")
        # VALIDATE CHANGES
        success = validatePatternExchange(g)
        if (success):
            # CHANGE PROPERTIES
            activateDefense(g, obj, "authenticated")
    # def longPattern(g):

    # def ex1P1(g):

    # #Every Identity that is connected to 2 or more application
    # x = g.V().match(\
    #     __.as_("identity").where(__.out("instanceOf")\
    #                             .hasLabel("Identity")),\

    #     __.as_("identity").where(__.out().out("instanceOf")\
    #                             .hasLabel("Application")\
    #                             .count().is_(P.gte(2))),\

    #     __.as_("identity").out().where(__.out("instanceOf")\
    #                                 .hasLabel("Application"))\
    #                     .fold().as_("apps"),\

    #     __.as_("identity")\
    #          .out().where(\
    #                     __.and_(\
    #                         __.not_(__.out("instanceOf")\
    #                         .hasLabel("Application")),\

    #                         __.out().out("instanceOf")\
    #                         .out("instanceOf")\
    #                         .hasLabel("assets")\
    #                     )\
    #                 )\
    #                 .fold().as_("neigbours"))\
    #     .select("identity","apps","neigbours" ).toList()
    # print(x)
    # #Replacement pattern needs to make the pattern unvalid buy for example making making the identy only connect to
    # #1 application
    # #Create get active defenses, and somehowe copy TTC??(maybe not) for attacksteps
    # for a in x:
    #     ## remove all but 1 connection
    #     for i in range(len(a['apps'])-1):
    #         roleOfApp = getRoleInAssociation(g, a['identity'], a['apps'][i])
    #         removeAssociation(g, a['identity'], a['apps'][i], roleOfApp)
    #         o = addNewObject(g, "Identity", "newId")
    #         link = getLinkName(g, a['identity'], a['apps'][i], roleOfApp)
    #         addNewAssociation(g, o, a['apps'][i], link)
    #         for j in range(len(a['neigbours'])):
    #             roleOfIdentity = getRoleInAssociation(g, a['neigbours'][j], a['identity'])
    #             link = getLinkName(g, a['neigbours'][j], a['identity'], roleOfIdentity)
    #             addNewAssociation(g, a['neigbours'][j], o, link)
    #     success = validatePatternExchange(g)

    #### Get all credential that has not a data connected and
    #  that is connected to a identity

    ### BAD PATTERN ###
    badPattern = g.V().match(__.as_("cred").where(__.out("instanceOf").hasLabel("Credentials")), \
 \
                             __.as_("cred").out("identities").where(__.out("instanceOf").hasLabel("Identity")).as_(
                                 "id"), \
 \
                             __.not_(__.as_("cred").out(). \
                                     where(__.out("instanceOf").hasLabel("Data").out().as_("id")))) \
        .select("cred", "id").toList()

    ### REWRITE PATTERN ###
    for a in badPattern:
        removeAssociation(g, a['cred'], a['id'], "identities")
        data = addNewObject(g, "Data", "data")
        addNewAssociation(g, a['cred'], data, "EncryptionCredentials")
        addNewAssociation(g, data, a['id'], "ReadPrivileges")

        success = validatePatternExchange(g)
        if (success):
            activateDefense(g, data, "authenticated")

    ### PAttern 3 ### all application that is not connected to another application.

    bp = g.V() \
        .match(__.as_("apps").where(__.out("instanceOf").hasLabel("Application")), \
               __.as_("apps").where(__.not_(__.out().out("instanceOf").hasLabel("Application")))) \
        .select("apps").toList()

    for p in bp:
        o = addNewObject(g, "Application", "newApp")
        addNewAssociation(g, p, o, "AppExecution")
        validatePatternExchange(g)

    # PATTERN 4
    # print(g.V().has("version", "").out("defense").properties().toList())

    # app = g.V().match(\
    #     __.as_("id").out("instanceOf")\
    #             .hasLabel("Application"),\

    #     __.as_("id").has("version", "2.1"),\

    #     __.as_("id").where(__.out("defense").and_(
    #                     __.out("instanceOf").\
    #                     hasLabel("disabled"),\

    #                     __.has("active", 0))),\

    #     __.as_("id").where(__.not_(\
    #         __.out().out("instanceOf").\
    #         hasLabel("RoutingFirewall")))).\
    #     select("id").toList()

    # print(app)

    # for a in app:
    #     o = addNewObject(g, "RoutingFirewall", "fw")
    #     addNewAssociation(g, a, o, "ManagedBy")
    #     success = validatePatternExchange(g)
    #     if(success):
    #         addTag(g, a, {"version": "3.0"})
    #         activateDefense(g, a, "disabled")

    #     print("Properties of the application: ",g.V(a.id).properties().toList())
    #     print("Properties of the defense: ",g.V(a.id).out("defense").where(__.out("instanceOf").hasLabel("disabled")).properties().toList())


# Add that it has unclassified data aswell??
def networkSegmentation1(g):
    # print(g.V().has('name', "nw1").out().where(__.out("instanceOf").hasLabel("Application").where(__.out())))
    antiPattern = g.V() \
        .match( \
        __.as_("nw") \
            .where( \
            __.out("instanceOf") \
                .hasLabel("Network")), \
 \
        __.as_("nw") \
            .out()
            .where( \
            __.out("instanceOf") \
                .hasLabel("Application")) \
            .has('type', 'Operating System') \
            .where( \
            __.out() \
                .where( \
                __.out("instanceOf") \
                    .hasLabel("Application")) \
                .has('type', 'Software Application') \
                .where( \
                __.out() \
                    .where(
                    __.out("instanceOf") \
                        .hasLabel("Data")) \
                    .has('type', 'Classified') \
                ) \
            ) \
            .fold() \
            .as_("confidentialComputers") \
        ) \
        .select('nw', 'confidentialComputers') \
        .toList()
    print(antiPattern)
    ### REWRITE PATTERN ###
    for p in antiPattern:
        # STRUCTURAL CHANGES
        # make sure that there is confidential data on the computer
        if (p['confidentialComputers']):
            newNw = addNewObject(g, "Network", "nw2")
            fw = addNewObject(g, "RoutingFirewall", "newFirewall")
            addNewAssociation(g, p['nw'], fw, "NetworkExposure", "networks")
            addNewAssociation(g, newNw, fw, "NetworkExposure", "networks")
            for app in p['confidentialComputers']:
                role = getRoleInAssociation(g, app, p['nw'])
                removeAssociation(g, app, p['nw'], role)
                addNewAssociation(g, app, newNw, "NetworkExposure", "applications")

        # VALIDATE CHANGES
        success = validatePatternExchange(g)

        # CHANGE PROPERTIES


def networkSegmentation2(g):
    antiPattern = g.V().match( \
        __.as_("nw") \
            .where( \
            __.out("instanceOf") \
                .hasLabel("Network")), \
 \
        __.as_("os") \
            .where( \
            __.out("instanceOf") \
                .hasLabel("Application")), \
 \
        __.as_("app") \
            .where( \
            __.out("instanceOf") \
                .hasLabel("Application")), \
 \
        __.as_("classifiedData") \
            .where( \
            __.out("instanceOf") \
                .hasLabel("Data")), \
 \
        __.as_("nw") \
            .out() \
            .as_("os"),

        __.as_("os") \
            .out() \
            .as_("app"),

        __.as_("app") \
            .out() \
            .as_("classifiedData"),

        __.as_("classifiedData") \
            .has('type', 'Classified'), \
 \
        __.as_("app") \
            .has('type', 'Software Application'), \
 \
        __.as_("os") \
            .has('type', 'Operating System') \
        ) \
        .select("nw", "os", "app", "classifiedData") \
        .toList()
    ### REWRITE PATTERN ###
    counter = 1
    for p in antiPattern:
        name1 = "newNetwork" + str(counter)
        name2 = "newFirewall" + str(counter)
        # STRUCTURAL CHANGES
        nw = addNewObject(g, "Network", name1)
        role = getRoleInAssociation(g, p['nw'], p['os'])
        removeAssociation(g, p['nw'], p['app'], role)
        fw = addNewObject(g, "Application", name2)
        addNewAssociation(g, nw, fw, "NetworkExposure")
        addNewAssociation(g, nw, p['app'], "NetworkExposure")

        # VALIDATE CHANGES
        success = validatePatternExchange(g)
        # CHANGE PROPERTIES
        if (success):
            counter += 1


def runTest(g):
    # threeConnectedInARow(g)
    # print(g.V().where(__.out("instanceOf").hasLabel("Application")).fold().toList())
    # updateInBetween(g)
    # twoConnectedWithFilters(g)
    # duplicateObject(g)
    # unwantedObject(g)
    # missingAssoc(g)
    networkSegmentation1(g)
    # networkSegmentation2(g)