#!/usr/bin/env/python
#
# api_request.py
#
# Python script, provided 'as-is', as an example of how to perform upgrades via API
#
# Dependencies:
# This library depends upon client.py, which depends on requests that can be installed via pip
#
# Usage:
#
#  (1) Change the parameters within the parameters section ONLY.
#  (2) Run the script from cli with 'python api_request.py'

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from client import VcoRequestManager
import os
import sys
import json

######## PARAMETERS ###########
# username expects env variable. Can be changed to a string
# password expects env variable. Can be changed to a string
# edgeList expects a list of edges
# operatorProfileName expects the OP name, as seen when doing api call to enterpriseProxy/getEnterpriseProxyOperatorProfiles
# Example:
# hostname = "vco1-region.velocloud.net"
# username = 'your@username.com'
# password = 'yourPa$$w0rd'
# client = VcoRequestManager(hostname)
# enterpriseId = 10
# edgeList = ['Edge 1'] 
# operatorProfileName = 'R332P1'

hostname = "vco.hostname.net"
username = os.environ["VC_USERNAME"] 
password = os.environ["VC_PASSWORD"]
client = VcoRequestManager(hostname)
enterpriseId = 0
edgeList = [''] 
operatorProfileName = '' 

######## END OF PARAMETERS ###########

def authenticate():
    """
    Perform user authentication
    """
    client.authenticate(username, password, False)

def getOperatorProfile():
    """ 
    Get operator profiles for this MSP and search for the OP id based on the name  
    """
    operatorProfileList = client.call_api("enterpriseProxy/getEnterpriseProxyOperatorProfiles", {"with": ["edges", "enterprises", "modules"]})
    for op in operatorProfileList:
        if op['name'] == operatorProfileName:
            if(op['configurationType'] == 'NETWORK_BASED'):
                print("Network based upgrades not supported by this script")
                sys.exit()
            operatorProfileId = op['id']
            print('Found operator profile \"%s\" with id %s' % (operatorProfileName, operatorProfileId))
            return operatorProfileId
    return None

def prepareUpgrade():
    """
    Collect the necessary information to perform the software upgrade and start it
    """
    # get the network id
    networkId = client.call_api('enterprise/getEnterprise', { 'id': enterpriseId })['networkId']

    # get the operator profile
    operatorProfileId = getOperatorProfile()
    if operatorProfileId is None:
        print('Operator profile \"%s\" not found. Cancelling upgrade' % operatorProfileName)
        sys.exit()
    
    # get the edgeId for each edge
    edges = client.call_api('enterprise/getEnterpriseEdgeList', {"with":["ha", "configuration"],"enterpriseId":enterpriseId})
    spokes = []
    hubs = []
    for edge in edges:
        if edge['name'] in edgeList:
            newEdge = {}
            newEdge['name'] = edge['name']
            newEdge['id'] = edge['id']
            if edge['isHub'] is True:
                hubs.append(newEdge)
            else:
                spokes.append(newEdge)

    # confirm upgrades and start them
    if(len(hubs) > 0):
        print("You're upgrading HUBS, it is always suggested to upgrade these first before doing spokes: ")
        for edge in hubs:
            print('\t- %s' % (edge['name']))
        if(confirmUpgrade("Should we start the hub upgrades?")):
            doUpgrade(hubs, operatorProfileId, networkId)
        else:
            print("Hub upgrades canceled. Cancelling upgrades to avoid any problems with spokes. If you need to upgrade spokes, remove the hubs from the edgeList")
            sys.exit(0)

    if(len(spokes) > 0):
        print("Spokes to upgrade: ")
        for edge in spokes:
            print('\t- %s' % (edge['name']))
        if(confirmUpgrade("Should we start the spoke upgrades?")):
            doUpgrade(spokes, operatorProfileId, networkId)
        else: 
            print("Spoke upgrades canceled")
            sys.exit(0)
    
def doUpgrade(edges, operatorProfileId, networkId):
    """
    Execute the API call to make the software upgrade. Takes a dict of edges along with the operatorProfile and the network id 
    """
    for edge in edges:
        # perform the software upgrade
        upgradeResult = client.call_api('edge/setEdgeOperatorConfiguration', {"edgeId": edge['id'], "enterpriseId": enterpriseId, "configurationId": operatorProfileId, "networkId": networkId})
        # check if the upgrade succeeded. Returns 1 indicating one row (operator profile) was modified. Else something went wrong 
        if json.dumps(upgradeResult) == '{"rows": 1}':
            print('Upgrade requested successfully for %s' % edge['name'])
        else:
            print('Something went wrong when requesting the upgrade for %s. Please check the VCO logs' % edge['name'])

def confirmUpgrade(message):
    answer = ""
    while answer not in ["y", "n"]:
        answer = raw_input("%s [Y/N]? " % message).lower()
    return answer == "y"

def main():
    if(len(edgeList) <= 0):
        print("No edges names in list, add edge names to the list (edgeList variable). Example: edgeList = ['velo1', 'velo2'] ")
        sys.exit(0)
    authenticate()
    prepareUpgrade()    
        
 
if __name__== "__main__":
    main()