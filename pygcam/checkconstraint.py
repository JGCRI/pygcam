#
# Check whether constraints are binding. The setup for an analysis may
# create conditions that result in binding constraints in the static
# case, but in Monte Carlo simulation, the constraints may no longer bind.
#
# This reads constraint and result files and checks that the values match
# within the desired tolerance, which can be specified in absolute or
# percentage terms.
#

from lxml import etree as ET
from pygcam.error import PygcamException, FileMissingError

def _getTextFor(parentNode, elementName):
    node = parentNode.find(elementName)
    return None if node is None else node.text


class Policy(object):
    def __init__(self, node):
            self.name   = node.get('name')
            self.type   = _getTextFor(node, 'policyType')
            self.market = _getTextFor(node, 'market-name')
            self.constraints = {}

            constraintNodes = node.findall('constraint')
            if constraintNodes is None:
                # maybe handle this with a schema file
                raise PygcamException('Missing constraint elements')

            for cnode in constraintNodes:
                year  = int(cnode.get('year'))
                value = float(cnode.text)
                self.constraints[year] = value

    def __str__(self):
        return '<Policy name=%s type=%s market=%s %s>' % (self.name, self.type, self.market, self.constraints)

class PolicyInfo(object):
    def __init__(self, regionNode):
        self.region = regionNode.get('name')
        self.policies = {}

        for policyNode in regionNode:
            obj = Policy(policyNode)
            self.policies[obj.name] = obj

class ConstraintInfo(object):

    def __init__(self, filename):
        """
        Read an XML file defining constraints.

        :param filename: (str) the path to an XML file holding constraint info
        :raises FileMissingError: if that the given filename does not exist
           or cannot be read.
        """
        try:
            parser = ET.XMLParser(remove_blank_text=True)
            tree = ET.parse(filename, parser)
        except:
            raise FileMissingError

        self.filename = filename
        self.regions = {}

        regionNodes = tree.findall('//region')
        for node in regionNodes:
            region = node.get('name')
            self.regions[region] = PolicyInfo(node)

        # if region or policyName not found...
        # raise PygcamException

    def getPolicy(self, region, policyName):
        try:
            policyInfo = self.regions[region]
        except KeyError:
            raise PygcamException('Region "%s" is not present in constraint file %s' % (region, self.filename))

        try:
            policy = policyInfo.policies[policyName]
        except:
            raise PygcamException('Policy "%s" is not present for region "%s" in constraint file %s' % \
                                  (policyName, region, self.filename))

        return policy

if __name__ == '__main__':
    filename = '/Users/rjp/bitbucket/otaq2016/pnnl-xml/FloorsMarch15/CornBDCellCeiling.xml'
    info = ConstraintInfo(filename)
    policy = info.getPolicy('USA', 'Biodiesel-Ceiling')
    print policy
