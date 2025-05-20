import sys
import os
import json

import xml.etree.ElementTree as ET
from time import gmtime, strftime

# Global variables
startTime = 'TIME'

targets = [] # Diretory list in 'target' directory
protocolName = 'NAME' # Protocol name
protocolDir = 'DIR' # protocol directory path
protocolXml = 'XML' # protocol.xml path

SiteList = [] # Diretory list in 'Site' directory
SiteLen = 'LENGTH'

searchKeyDict = {} # search key dictionary
searchKeys = [] # search key list

jsonMap = {} # Json list
valueDic = {} # Parameters' value dictionary
result = {} # Result

# Pre-processing
# (1) Parse protocol.xml
# (2) List Site directories'(for UIRx.xml & session.xml) name 
# (3) Load search key
# (4) Excute Main controller
def prime():
    global SiteList
    global SiteLen
    
    SiteList = [] # SiteList initialization

    # Parse the protocol.xml file
    try:
        tree = ET.parse(protocolXml)
        root = tree.getroot()
    except Exception as error:
        print("Fail to parse.", error)
        sys.exit()

    # Extract directories' name between 'Site' and 'UIRx'
    for location in root.findall('.//{http://ct.med.xy.com/atr/atrschema}location'):
        path = location.text.strip()
        startIndex = path.find('Site/') + len('Site/')
        endIndex = path.find('/UIRx')
        if startIndex != -1 and endIndex != -1:
            SiteList.append(path[startIndex:endIndex])
        
    SiteLen = len(SiteList)

    main()

# Main (controller)
# (1) Parse 'UIRx.xml' & 'session.xml'
# (2) Extract parameters
# (3) Create Json
def main():
    global protocolDir
    global result

    dirNo = 1

    for dirName in SiteList:
        UIRxPath = protocolDir + '/' + 'Site/' + dirName + '/UIRx.xml'
        sessionPath = protocolDir + '/' +'Site/' + dirName + '/session.xml'

        # Parse the 'UIRx.xml' file
        try:
            UIRxTree = ET.parse(UIRxPath)
            UIRxRoot = UIRxTree.getroot()
        except Exception as error:
            print("Fail to parse UIRx.xml; exit;", error)
            sys.exit()

        # Parse the 'session.xml' file
        try:
            sessionTree = ET.parse(sessionPath)
            sessionRoot = sessionTree.getroot()
        except Exception as error:
            print("Fail to parse session.xml; exit;", error)
            sys.exit()

        result.update({f'#{dirNo}':{f'{dirName}':{}}})

        # Extract series & prameter settings
        try:
            extractSession(dirNo, dirName, UIRxRoot, sessionRoot)
        except Exception as error:
            print("Fail to extract protocol information;", error)
        
        dirNo += 1

    try:
        createTxt()
    except Exception as error:
        print("Fail to create text for information;", error)

# Extract Series No. & Scan Types from 'session.xml'
def extractSession(dirNo, dirName, UIRxxml, sessionxml):
    global result
    
    # Define the namespace dynamically
    sessionNs = {'ns1': sessionxml.tag.split('}')[0].strip('{')}

    seriesCount = 1
    scanTypes = []

    for series in sessionxml.findall(".//ns1:task", sessionNs):
        
        nameAttr = series.attrib.get('type', '')
        
        # Task type const
        CTProtocolTask = "com.xy.med.ct.wfplat.study.sessionservice.task.impl.CTProtocolTask"
        CTSeriesTask = "com.xy.med.ct.wfplat.study.sessionservice.task.impl.CTSeriesTask"
        CTSettingsTask = "com.xy.med.ct.wfplat.study.sessionservice.task.impl.CTSettingsTask"
        CTIntellPrepTask = "com.xy.med.ct.wfplat.study.intellpreptask.impl.CTIntellPrepTask"

        # If task type = 'CTProtocolTask', we can extract description
        if nameAttr == CTProtocolTask:
            description = series.find(".//ns1:property[@name='DESCRIPTION']", sessionNs).attrib.get('value', '')
            result[f'#{dirNo}'][f'{dirName}'].update({f'{description}':{}})

        # If task type = 'CTSeriesTask', we can extract series number
        if nameAttr == CTSeriesTask:
            result[f'#{dirNo}'][f'{dirName}'][f'{description}'].update({f'Series {seriesCount}':{}})
            seriesCount +=1

        # If task type = 'CTSettingsTask' or 'CTIntellPrepTask', we can extract scan type
        if (nameAttr == CTSettingsTask) or (nameAttr == CTIntellPrepTask):
            
            try:
                type = series.find(".//ns1:property[@name='type']", sessionNs)
            except:
                raise Exception("Fail to find 'type' property")
            
            if 'INTELLPREP' in type:
                scanTypes.append(scanType.attrib['value'])
            else:
                scanType = series.find(".//ns1:property[@name='scanType']", sessionNs)
                scanTypes.append(scanType.attrib['value'])
    
    try:
        extractParams(dirNo, dirName, description, scanTypes, UIRxxml)
    except Exception as error:
        print("Fail to extract parameter", error)
        raise
                
# Extract Scan Parameters from 'UIRx.xml'
def extractParams(dirNo, dirName, description, scanTypes, UIRxxml):
    global result

    # Define the namespace dynamically
    UIRxNs = {'ns0': UIRxxml.tag.split('}')[0].strip('{')}

    seriesNo = 0

    for UIRxSeries in UIRxxml.findall('.//ns0:series', UIRxNs):
        seriesNo += 1
        groupCount = 1

        scanCID = UIRxSeries.find(".//ns0:ulement[@name='scanClinicalIdKey']", UIRxNs).attrib['value']

        for UIRxGroup in UIRxSeries.findall('.//ns0:group', UIRxNs):
            groupParams = {}
            
            # Input scan type for each group
            if len(scanTypes) > 0:
                groupParams.update({f'Scan Type':scanTypes[0]})
                del scanTypes[0]
            else:
                raise Exception("Number of Scan type does NOT match number of Group.")
            
            groupParams.update({f'Scan CID':scanCID})
            
            # Extract scan parameters
            for UIRxGroupElement in UIRxGroup:
                
                if not('recon' in UIRxGroupElement.tag):
                    elementName = UIRxGroupElement.attrib['name']

                    for searchKey in searchKeys:
                        
                        if elementName == searchKey:
                            value = UIRxGroupElement.attrib['value']

                            groupParams.update(translate(searchKey, value))
                else:
                    break

            result[f'#{dirNo}'][f'{dirName}'][f'{description}'][f'Series {seriesNo}'].update({f'Group {groupCount}': groupParams})

            # Extract recon parameters        
            reconCount = 1
            
            for UIRxRecon in UIRxGroup.findall('.//ns0:recon', UIRxNs):
                reconParams = {}

                for searchKey in searchKeys:
                    searchKeyElements = UIRxRecon.findall(f'.//ns0:ulement[@name="{searchKey}"]', UIRxNs)

                    for element in searchKeyElements:
                        value = element.attrib['value']

                        reconParams.update(translate(searchKey, value))

                result[f'#{dirNo}'][f'{dirName}'][f'{description}'][f'Series {seriesNo}'][f'Group {groupCount}'].update({f'Recon {reconCount}': reconParams})
                reconCount += 1
            
            groupCount += 1
    
    if len(scanTypes) > 0:
       raise Exception("Number of Scan type does NOT match number of Group.")
    
    motion = {0:'-', 1:'\\', 2:'|', 3:'/'}
    
    if not (dirNo == SiteLen):
        print(f'{motion[dirNo % 4]} Processing.. [{dirNo}/{SiteLen}] ', end = '\r')
    else:
        print(f'Processing Completed. [{dirNo}/{SiteLen}]')

def createTxt():
    global protocolName
    global result

    resultTxt = protocolName + '.txt'
    # Open a text file to write the extracted information
    with open(resultTxt, 'w') as file:
        txtHeader = ['SessionNo','SessionName','Protocol','SeriesNo','GroupNo','Parameters']

        file.write(f'\t{startTime} Generated.\n')

        for header in txtHeader:
            file.write(f'{header}\t')
        file.write('\n')

        for dirNo in list(result)[0:]:
            file.write(f'{dirNo}')

            for dirName in list(result[dirNo])[0:]:
                file.write(f'\t{dirName}')

                for description in list(result[dirNo][dirName])[0:]:
                    file.write(f'\t{description}')

                    seriesCount = 1
                    for seriseNo in list(result[dirNo][dirName][description])[0:]:
                        if seriesCount == 1:
                            file.write(f'\t{seriseNo}')
                        else:
                            file.write(f'\t\t\t{seriseNo}')

                        seriesCount += 1

                        groupCount = 1
                        for groupNo in list(result[dirNo][dirName][description][seriseNo])[0:]:
                            if groupCount == 1:
                                file.write(f'\t{groupNo}')
                            else:
                                file.write(f'\t\t\t\t{groupNo}')
                            
                            groupCount += 1

                            paramCount = 1
                            for params in list(result[dirNo][dirName][description][seriseNo][groupNo])[0:]:
                                if paramCount == 1:
                                    file.write(f'\t{params}\t')
                                else:
                                    file.write(f'\t\t\t\t\t{params}\t')

                                paramCount += 1

                                reconParam = 1
                                for paramValue in list(result[dirNo][dirName][description][seriseNo][groupNo][params])[0:]:
                                    
                                    if len(paramValue) > 1:
                                            if reconParam == 1:
                                                file.write(f'{paramValue}\t')
                                                reconParam += 1
                                            else:
                                                file.write(f'\n\t\t\t\t\t\t')
                                                file.write(f'{paramValue}\t')
                                            
                                            for reconParamValue in list(result[dirNo][dirName][description][seriseNo][groupNo][params][paramValue])[0:]:
                                                file.write(f'{reconParamValue}')

                                    else:
                                        file.write(f'{paramValue}')
                                
                                file.write('\n')

    print(f"Create '{resultTxt}' successfully")

# json Loader
def jsonLoader(jsonName):
    
    targetJson = 'json/' + jsonName
    try:
        with open(targetJson, 'r') as file:
            data = json.load(file)
    except Exception as error:
        print(f"Fail to load {jsonName}.json;", error)
    
    file.close()
    return data

# global variable set from json
def createDictionary():
    global searchKeyDict
    global searchKeys
    global valueDic

    jsonDir = 'json/'
    jsons = os.listdir(jsonDir)

    for json in jsons:

        if json == "searchKey.json":
            try:
                searchKeyDict = jsonLoader(json)
                searchKeys = list(searchKeyDict.keys())
            except:
                print(f"[Warning] {jsonMap[json]} unavailable.")
                pass

        elif json == "jsonMap.json":
            pass

        elif json in jsonMap:
            try:
                valueDic.update(jsonLoader(json))
            except:
                print(f"[Warning] {jsonMap[json]} dictionary unavailable.")
                pass
        else:
            print(f"Except {json}" ) 

def translate(key, value):

    transkey = searchKeyDict[key]

    if(transkey in valueDic.keys()):
        try:
            if(transkey == "Recon Clinical Identifier"):
                value = valueDic[transkey][f'{int(int(value) / 100)}'][value]
            else:
                value = valueDic[transkey][value]
        except KeyError:
            print(f"Not valid value: {value} ({transkey})")
    else:
        pass

    return {f'{transkey}':value}

# Init
if __name__ == '__main__':

    # Create reference from jsons
    try:
        jsonMap = jsonLoader('jsonMap.json')
        createDictionary()
    except Exception as error:
        print("Fail to create Dictionary;", error)

    targetDir = 'target/'
    targets = os.listdir(targetDir)

    for target in targets:
        if os.path.isdir(targetDir + target):
            startTime = strftime("%Y-%m-%d %H:%M:%S", gmtime())
            print(f'<< {target} protocol [{startTime}]>>')
            protocolName = target
            protocolDir = targetDir + target
            protocolXml = targetDir + target + '/' + target + '.xml'
            prime()
        else:
            continue

