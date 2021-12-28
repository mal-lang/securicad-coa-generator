from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.graph_traversal import __
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from graphModels import drop_all, mal, readMALSpec, addAssets, addAssociations, xmlToModel
from rules import runTest
from propertyGraphtoXML import *


def connect_graph_db():
    connection = DriverRemoteConnection('ws://localhost:8182/gremlin', 'g')
    g = traversal().withRemote(connection)

    drop_all(g)
    #MAL layer
    mal(g)

    # DSL layer
    url1 = "https://raw.githubusercontent.com/mal-lang/coreLang/master/src/main/mal/coreLang.mal"
    url2 = "https://raw.githubusercontent.com/mal-lang/coreLang/v0.2.0/src/main/mal/SoftwareVulnerability.mal"
    url3 = "https://raw.githubusercontent.com/mal-lang/coreLang/v0.2.0/src/main/mal/coreVulnerability.mal"

    asse = []
    asso = []
    assets, assocs = readMALSpec(url1)
    asse.append(assets)
    asso.append(assocs)
    # addAssets(g, assets)
    # addAssociations(g, assocs)

    assets, assocs = readMALSpec(url2)
    asse.append(assets)
    asso.append(assocs)
    # addAssets(g, assets)
    # addAssociations(g, assocs)

    assets, assocs = readMALSpec(url3)
    asse.append(assets)
    asso.append(assocs)

    addAssets(g, asse)
    addAssociations(g, asso)

    s = xmlToModel(g, './data-models/nw-segmentation-reworked.sCAD', './data-models/nw-segmentation-rework.csv')

    runTest(g)
    convertPropertyGraphToSecuriCAD(g, s)
    print( "The program has now finished")

    connection.close()