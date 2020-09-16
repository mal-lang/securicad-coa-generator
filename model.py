import xml.etree.ElementTree as ET


class Model:
    '''
    An abstraction of a model created with securilang of securiCAD enterprise.

    Model ~ xml.etree.ElementTree of the .eom file storing the securiCAD model.
    '''
    def __init__(self, path=".eom"):
        assert path[-4:] == ".eom"
        try:
            with open(path, 'rt') as f:
                self.tree = ET.parse(f)
                self.root = self.tree.getroot()
                self.name = path.split('\\')[-1] # file name
                self.path = path
        except:
            print('Failed to initialize Model object using the following path: {}'.format(path))
            return


    def count_objects_in_the_model(self):
        return len([object for object in self.root.iter("objects")])


    def defenses_applicable_to_object(self, objectExportedID=None):
        '''
        In: string storing an object's ID
        Out: set of strings

        Given objectExporedId of an object in the model, return the set of names
        of defense steps that can be applied to this object.
        '''
        try:
            int(objectExportedID)
        except:
            print("Exported ID should be a string containing an integer.")

        metaConcept = None

        for object in self.root.iter("objects"):
            if object.attrib['exportedId'] == objectExportedID:
                metaConcept = object.attrib['metaConcept']
                break

        if metaConcept is None:
            return set()

        # the "defenseDefaultValueConfigurations" parts are listed for some of the assets.
        # e.g., for SoftwareProduct, but not for UnknownSoftwareProduct. assuming that they
        # are the same, in the case of 'unknowns', we refer to the specification of 'knowns'.
        if len(metaConcept) > 7 and metaConcept[:7] == 'Unknown':
            metaConcept = metaConcept[7:]

        for node in self.root.iter("defenseDefaultValueConfigurations"):
            if node.attrib["metaConcept"] == metaConcept:
                result = []
                for child in node.iter("attributeConfigurations"):
                    result.append(child.attrib["metaConcept"])
                return set(result)
            # TODO: something is wrong with UnknownAccessControl?  <- this comment is old, I don't remember what was the problem
        return set()


    def turn_defense_on(self, objectExportedID, defenseName, checkValidity=True):
        '''
        Update the model by setting the probability of the defense 'defenseName'
        being functional on object having exported ID 'objectExportedId' to 1.

        So, turn the defense on.
        '''
        if checkValidity:
            # check if the defense provided can be applied to the object
            if defenseName not in self.defenses_applicable_to_object(objectExportedID):
                return
        objectNode = [object for object in self.root.iter(
            "objects") if object.attrib['exportedId'] == objectExportedID][0]

        # check if the node corresponding to the object already has a child corresponding to the defense, i.e.,
        # if the defense has a non-default probability value assigned already.
        for child in objectNode:
            if "metaConcept" in child.attrib and child.attrib["metaConcept"] == defenseName:
                # the defense is there. change its probability value to 1.
                # probability is specified in the grandchild of the node corresponding to the defense.
                # we change the value by removing this grandchild and creating a new one. quick solution. :)
                # // grandchild of defense = grandgrandchild of the object node
                child[0].remove(child[0][0])
                grandgrandchild = ET.Element("parameters", {
                                             "name": "probability", "value": "1.0"})
                child[0].append(grandgrandchild)
                return

        # the defense is not there, so its probability value is set to the default.
        child = ET.Element("evidenceAttributes", {
                           "description": "", "metaConcept": defenseName})
        grandchild = ET.Element("evidenceDistribution", {"type": "Bernoulli"})
        grandgrandchild = ET.Element("parameters", {
                                     "name": "probability", "value": "1.0"})
        objectNode.append(child)
        child.append(grandchild)
        grandchild.append(grandgrandchild)
        return


    def write_to_file(self, new_path=None):
        '''
        Save the model as an .eom file that can be provided to securiCAD enterprise.
        Return the path to the file.

        If no path name is provided, a new file is created under the same path, with the file name
        being 'updated_' followed by the old name.
        '''
        output = b'<?xml version="1.0" ?>\n'
        output += b'<com.foreseeti.kernalCAD:XMIObjectModel integerUniformJumpRange="1" samples="100" samplingMethod="FORWARD" warningThreshold="100" xmi:version="2.0" xmlns:com.foreseeti.kernalCAD="http:///com/foreseeti/ObjectModel.ecore" xmlns:xmi="http://www.omg.org/XMI">'
        the_rest = ET.tostring(self.tree.getroot())
        the_rest = the_rest[the_rest.index(b'\n'):][:-21]
        output += the_rest
        output += b"</com.foreseeti.kernalCAD:XMIObjectModel>\n"
        if new_path is None:
            newFileName = "updated_{}".format(self.name)
            nameStartsHere = self.path.rindex('\\')
            new_path = self.path[:nameStartsHere+1] + newFileName
        with open(new_path, 'wb') as f:
            f.write(output)
        return new_path


    def get_exportedId_from_id(self, id=""):
        for object in self.root.iter("objects"):
            if object.attrib['id'] == id:
                return object.attrib['exportedId']
        return


    def get_id_from_exportedId(self, exportedId=""):
        for object in self.root.iter("objects"):
            if object.attrib['exportedId'] == exportedId:
                return object.attrib['id']
        return