import sys
import os
import time
import json
import csv

import xml.etree.ElementTree as ET

# Global variables
_start_time = 'TIME'

_targets = [] # Diretory list in 'target' directory
_protocol_name = 'NAME' # Protocol name
_protocol_dir = 'DIR' # protocol directory path
_protocol_xml = 'XML' # protocol.xml path

_site_list = [] # Diretory list in 'Site' directory
_site_len = 'LENGTH'

_search_key_dict = {} # search key dictionary
_search_keys = [] # search key list

_json_map = {} # Json list
_value_dict = {} # Parameters' value dictionary
_result = {} # result

# Pre-processing
# (1) Parse protocol.xml
# (2) List Site directories'(for UIRx.xml & session.xml) name 
# (3) Excute Main controller
def prime():
    global _site_list
    global _site_len
    
    _site_list = [] # _site_list initialization

    # (1) Parse the protocol.xml file
    try:
        tree = ET.parse(_protocol_xml)
        root = tree.getroot()
    except Exception as error:
        print("Fail to parse.", error)
        sys.exit()

    # (2) Extract directories' name between 'Site' and 'UIRx'
    for location in root.findall('.//{http://ct.med.xy.com/atr/atrschema}location'):
        path = location.text.strip()
        start_index = path.find('Site/') + len('Site/')
        end_index = path.find('/UIRx')
        if start_index != -1 and end_index != -1:
            _site_list.append(path[start_index:end_index])
        
    _site_len = len(_site_list)

    # (3) Excute Main controller
    main()

# Main (controller)
# (1) Parse 'UIRx.xml' & 'session.xml'
# (2) Extract parameters
# (3) Create .txt
# (4) Convert .txt to .csv
def main():
    global _protocol_dir
    global _result
    global _protocol_name

    dir_no = 1

    for dir_name in _site_list:
        UIRx_path = _protocol_dir + '/' + 'Site/' + dir_name + '/UIRx.xml'
        session_path = _protocol_dir + '/' +'Site/' + dir_name + '/session.xml'

        # (1)-a Parse the 'UIRx.xml' file
        try:
            UIRx_tree = ET.parse(UIRx_path)
            UIRx_root = UIRx_tree.getroot()
        except Exception as error:
            print("Fail to parse UIRx.xml; exit;", error)
            sys.exit()

        # (1)-b Parse the 'session.xml' file
        try:
            session_tree = ET.parse(session_path)
            session_root = session_tree.getroot()
        except Exception as error:
            print("Fail to parse session.xml; exit;", error)
            sys.exit()

        _result.update({f'#{dir_no}':{f'{dir_name}':{}}})

        # (2) Extract series & prameter settings
        try:
            extract_session(dir_no, dir_name, UIRx_root, session_root)
        except Exception as error:
            print("Fail to extract protocol information;", error)
        
        dir_no += 1

    txt_file_name = _protocol_name + "_" + time.strftime("%Y%m%d%H%M%S", time.gmtime())
    # (3) Create .txt
    try:
        create_info_txt(txt_file_name)
    except Exception as error:
        print("Fail to create text for information;", error)
    
    # (4) Convert .txt to .csv
    try:
        convert_txt_to_csv(txt_file_name)
    except Exception as error:
        print("Fail to convert text to csv;", error)

# Extract Series No. & Scan Types from 'session.xml'
def extract_session(dir_no, dir_name, UIRx_xml, session_xml):
    global _result
    
    # Define the namespace dynamically
    session_ns = {'ns1': session_xml.tag.split('}')[0].strip('{')}

    series_count = 1
    scan_types = []

    for series in session_xml.findall(".//ns1:task", session_ns):
        
        name_attr = series.attrib.get('type', '')
        
        # Task type const
        CT_protocol_task = "com.xy.med.ct.wfplat.study.sessionservice.task.impl.CTProtocolTask"
        CT_series_task = "com.xy.med.ct.wfplat.study.sessionservice.task.impl.CTSeriesTask"
        CT_settings_task = "com.xy.med.ct.wfplat.study.sessionservice.task.impl.CTSettingsTask"
        CT_IntellPrep_Task = "com.xy.med.ct.wfplat.study.intellpreptask.impl.CTIntellPrepTask"

        # If task type = 'CTProtocolTask', we can extract description
        if name_attr == CT_protocol_task:
            description = series.find(".//ns1:property[@name='DESCRIPTION']", session_ns).attrib.get('value', '')
            _result[f'#{dir_no}'][f'{dir_name}'].update({f'{description}':{}})

        # If task type = 'CTSeriesTask', we can extract series number
        if name_attr == CT_series_task:
            _result[f'#{dir_no}'][f'{dir_name}'][f'{description}'].update({f'Series {series_count}':{}})
            series_count +=1

        # If task type = 'CT_settings_task' or 'CT_IntellPrep_Task', we can extract scan type
        if (name_attr == CT_settings_task) or (name_attr == CT_IntellPrep_Task):
            
            try:
                type = series.find(".//ns1:property[@name='type']", session_ns)
            except:
                raise Exception("Fail to find 'type' property")
            
            ## If Type = 'INTELLPREP', scan type is type.value
            if 'INTELLPREP' in type:
                scan_types.append(scan_type.attrib['value'])
            ## If Type != 'INTELLPREP', scan type is scanType.value
            else:
                scan_type = series.find(".//ns1:property[@name='scanType']", session_ns)
                scan_types.append(scan_type.attrib['value'])
    
    # Extract parameter, parameter's value
    try:
        extract_params(dir_no, dir_name, description, scan_types, UIRx_xml)
    except Exception as error:
        print("Fail to extract parameter", error)
        raise
                
# Extract Scan Parameters from 'UIRx.xml'
def extract_params(dir_no, dir_name, description, scan_types, UIRx_xml):
    global _result

    # Define the namespace dynamically
    UIRx_ns = {'ns0': UIRx_xml.tag.split('}')[0].strip('{')}

    series_no = 0

    ## Find address of 'series'
    for UIRx_series in UIRx_xml.findall('.//ns0:series', UIRx_ns):
        series_no += 1
        group_count = 1

        scan_CID = UIRx_series.find(".//ns0:ulement[@name='scanClinicalIdKey']", UIRx_ns).attrib['value']

        ## Find address of 'group'
        for UIRx_group in UIRx_series.findall('.//ns0:group', UIRx_ns):
            group_params = {}
            
            ## Input scan type for each group
            if len(scan_types) > 0:
                group_params.update({f'Scan Type':scan_types[0]})
                del scan_types[0]
            else:
                raise Exception("Number of Scan type does NOT match number of Group.")
            
            group_params.update({f'Scan CID':scan_CID})
            
            ## Extract scan parameters for each group
            for UIRx_group_element in UIRx_group:
                
                ### Except for recons for other groups
                if not('recon' in UIRx_group_element.tag):
                    element_name = UIRx_group_element.attrib['name']

                    ### name contrast with search key
                    for search_key in _search_keys:
                        
                        if element_name == search_key:

                            value = UIRx_group_element.attrib['value']

                            if(UIRx_group_element.get('visible') != 'false'):
                                group_params.update(translate(search_key, value))
                else:
                    break

            _result[f'#{dir_no}'][f'{dir_name}'][f'{description}'][f'Series {series_no}'].update({f'Group {group_count}': group_params})

            ## Extract scan parameters for each recon       
            recon_count = 1
            
            ### Find address of 'recon'
            for UIRx_recon in UIRx_group.findall('.//ns0:recon', UIRx_ns):
                recon_params = {}

                ## Extract recon parameters for each recon
                for UIRx_recon_element in UIRx_recon:

                ### Except for subrecons for other recons
                    if not('subrecon' in UIRx_recon_element.tag):
                        element_name = UIRx_recon_element.attrib['name']

                        ### Find address of 'search key'
                        for search_key in _search_keys:
                            search_key_elements = UIRx_recon.findall(f'.//ns0:ulement[@name="{search_key}"]', UIRx_ns)

                            for element in search_key_elements:
                                
                                value = element.attrib['value']

                                if(element.get('visible') != 'false'):
                                    recon_params.update(translate(search_key, value))
                    else:
                        break

                    if(recon_count == 1):
                        _result[f'#{dir_no}'][f'{dir_name}'][f'{description}'][f'Series {series_no}'][f'Group {group_count}'].update({f'Primary Recon': recon_params})
                    else:
                        _result[f'#{dir_no}'][f'{dir_name}'][f'{description}'][f'Series {series_no}'][f'Group {group_count}'].update({f'Secondary Recon {recon_count-1}': recon_params})
                    
                ## Extract scan parameters for each recon       
                subrecon_count = 1

                ### Find address of 'recon'
                for UIRx_subrecon in UIRx_group.findall('.//ns0:subrecon', UIRx_ns):
                    subrecon_params = {}

                    ### Find address of 'search key'
                    for search_key in _search_keys:
                        search_key_elements = UIRx_subrecon.findall(f'.//ns0:ulement[@name="{search_key}"]', UIRx_ns)

                        for element in search_key_elements:
                            
                            value = element.attrib['value']

                            if(element.get('visible') != 'false'):
                                subrecon_params.update(translate(search_key, value))
                        
                    if(recon_count == 1):
                        _result[f'#{dir_no}'][f'{dir_name}'][f'{description}'][f'Series {series_no}'][f'Group {group_count}']['Primary Recon'].update({f'Sub Recon {subrecon_count}': subrecon_params})
                    else:
                        _result[f'#{dir_no}'][f'{dir_name}'][f'{description}'][f'Series {series_no}'][f'Group {group_count}'][{f'Secondary Recon {recon_count-1}'}].update({f'Sub Recon {subrecon_count}': subrecon_params})

                    subrecon_count += 1
                
                recon_count += 1
            
            group_count += 1
    
    if len(scan_types) > 0:
       raise Exception("Number of Scan type does NOT match number of Group.")
    
    motion = {0:'-', 1:'\\', 2:'|', 3:'/'}
    
    if not (dir_no == _site_len):
        print(f'{motion[dir_no % 4]} Processing.. [{dir_no}/{_site_len}] ', end = '\r')
    else:
        print(f'Processing Completed. [{dir_no}/{_site_len}]')

# Write '-----' x5
def header_border_line(file):
        
    header_border_line = '-----'
    
    for i in range(5):
        file.write(header_border_line)
        file.write('\t')
    file.write('\n')

# Write '*****' x5
def dividing_line(file):
        
    division_line = '*****'
    
    for i in range(5):
        file.write(division_line)
        file.write('\t')
    file.write('\n')

# Write New line (Enter↲)
def new_line(file):
    
    file.write('\n')

# Get file's modified date information
def get_file_mtime(file_path):

    mtime = time.ctime(os.path.getmtime(file_path))

    return mtime

# Write Header
def header(file):
    global _protocol_name
    global _protocol_xml

    header_row1 = ['Session#','Session Name','File List']
    header_row2 = ['Protocol Name','Series#','Group#','Parameters']

    ## Write Header Border Line <Head>
    header_border_line(file)

    ## Write Execute time
    file.write(f'{time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())} Generated.')
    new_line(file)
    
    ## Write ctime/mtime of 'protocol'.xml
    get_date_info(file, _protocol_name, _protocol_xml)
    
    ## Write Header row1
    for header in header_row1:
        file.write(f'{header}\t')
    new_line(file)

    ## Write Division Line
    dividing_line(file)

    ## Write Header row2
    for header in header_row2:
        file.write(f'{header}\t')
    new_line(file)

    ## Write Header Border Line <Tail>
    header_border_line(file)
    new_line(file)

def get_date_info(file, file_name, file_path):
    
    file.write(f'{file_name}.xml\t')
    file.write(f'{get_file_mtime(file_path)} Modified.\t')
    new_line(file)

def set_xml_path(dir_name, xml_name):
    global _protocol_dir

    xml = xml_name + '.xml'

    xml_path = _protocol_dir + '/' + 'Site' + '/' + dir_name + '/' + xml

    return xml_path

# Create protocol information txt
def create_info_txt(file_name):
    global _protocol_dir
    global _result

    result_txt = file_name + '.txt'
    # Open a text file to write the extracted information
    with open(result_txt, 'w') as file:
        
        ## Write Header
        header(file)

        ## Write Contentes
        ### Write target directory number
        for dir_no in list(_result)[0:]:
            new_line(file)
            file.write(f'{dir_no}')

            ### Write target directory name
            for dir_name in list(_result[dir_no])[0:]:
                file.write(f'\t{dir_name}')

                file.write('\t')
                get_date_info(file, 'UIRx', set_xml_path(dir_name, 'UIRx'))
                file.write('\t\t')
                get_date_info(file, 'session', set_xml_path(dir_name, 'session'))

                dividing_line(file)
                new_line(file)

                ### Write target description
                for description in list(_result[dir_no][dir_name])[0:]:
                    file.write(f'{description}')

                    ### Write series number
                    series_count = 1
                    for serise_no in list(_result[dir_no][dir_name][description])[0:]:
                        if series_count == 1:
                            file.write(f'\t{serise_no}')
                        else:
                            file.write(f'\t{serise_no}')


                        series_count += 1

                        ### Write group number
                        group_count = 1
                        for group_no in list(_result[dir_no][dir_name][description][serise_no])[0:]:
                            if group_count == 1:
                                file.write(f'\t{group_no}')
                            else:
                                file.write(f'\t\t{group_no}')
                            
                            group_count += 1

                            ### Write group parameter and parameter's value
                            param_count = 1
                            for params in list(_result[dir_no][dir_name][description][serise_no][group_no])[0:]:
                                if param_count == 1:
                                    file.write(f'\t{params}\t')
                                else:
                                    file.write(f'\t\t\t{params}\t')

                                param_count += 1

                                ### Write group's recon parameter and parameter's value
                                recon_param = 1
                                for recon_params in list(_result[dir_no][dir_name][description][serise_no][group_no][params])[0:]:
                                    
                                    if len(recon_params) > 1:
                                        if recon_param == 1:
                                            file.write(f'{recon_params}\t')
                                            recon_param += 1
                                        else:
                                            new_line(file)
                                            file.write(f'\t\t\t\t')
                                            file.write(f'{recon_params}\t')

                                        ### Write reson's subrecon parameter and parameter's value
                                        sub_recon_param = 1
                                        for recon_param_value in list(_result[dir_no][dir_name][description][serise_no][group_no][params][recon_params])[0:]:
                                            
                                            if len(recon_param_value) > 1:
                                                if sub_recon_param == 1:
                                                    file.write(f'{recon_param_value}\t')
                                                    sub_recon_param += 1
                                                else:
                                                    new_line(file)
                                                    file.write(f'\t\t\t\t\t')
                                                    file.write(f'{recon_param_value}\t')

                                                for subrecon_params_value in list(_result[dir_no][dir_name][description][serise_no][group_no][params][recon_params][recon_param_value])[0:]:
                                                    file.write(f'{subrecon_params_value}')
                                            
                                            else:
                                                file.write(f'{recon_param_value}')

                                    else:
                                        file.write(f'{recon_params}')
                                
                                new_line(file)

    print(f"Create '{result_txt}' successfully")

# Convert .txt to .csv
def convert_txt_to_csv(file_name):
    input_file_path = file_name + '.txt'
    output_file_path = file_name + '.csv'
    delimiter = '\t'  # Adjust based on your text file's delimiter

    with open(input_file_path, 'r') as infile, open(output_file_path, 'w', newline='') as outfile:
        reader = csv.reader(infile, delimiter=delimiter)
        writer = csv.writer(outfile)

        for row in reader:
            writer.writerow(row)

    print(f"Create '{file_name}.csv' successfully")

# json Loader
def json_loader(json_name):
    
    target_json = 'json/' + json_name
    try:
        with open(target_json, 'r') as file:
            data = json.load(file)
    except Exception as error:
        print(f"Fail to load {json_name}.json;", error)
    
    file.close()
    return data

# global variable set from json
def create_dictionary():
    global _search_key_dict
    global _search_keys
    global _value_dict

    # Refer 'json' directory and list up directories in 'json'
    json_dir = 'json/'
    jsons = os.listdir(json_dir)

    for json in jsons:

        if json == "searchKey.json":
            try:
                _search_key_dict = json_loader(json)
                _search_keys = list(_search_key_dict.keys())
            except:
                print(f"[Warning] {_json_map[json]} unavailable.")
                pass

        elif json == "jsonMap.json":
            pass

        elif json in _json_map:
            try:
                _value_dict.update(json_loader(json))
            except:
                print(f"[Warning] {_json_map[json]} dictionary unavailable.")
                pass
        else:
            print(f"Except {json}" ) 

# Translate value
def translate(key, value):

    trans_key = _search_key_dict[key]

    if(trans_key in _value_dict.keys()):
        try:
            if(trans_key == "Recon Clinical Identifier"):
                value = _value_dict[trans_key][f'{int(int(value) / 100)}'][value]
            else:
                value = _value_dict[trans_key][value]
        except KeyError:
            print(f"Not valid value: {value} ({trans_key})")
    else:
        pass

    return {f'{trans_key}':value}

# Init
if __name__ == '__main__':

    # Create value dictionary from jsons
    try:
        _json_map = json_loader('jsonMap.json')
        create_dictionary()
    except Exception as error:
        print("Fail to create Dictionary;", error)

    # Refer 'target' directory and list up directories in 'target'
    # Ex) target/ATR_Z1_40mm, target/ATR_Z2_40mm, ...
    _target_dir = 'target/'
    _targets = os.listdir(_target_dir)

    # Proceed for each target
    # e.g) targets = target/ATR_Z1_40mm, target/ATR_Z2_40mm
    # THEN, target = ATR_Z1_40mm → ATR_Z2_40mm
    for _target in _targets:
        if os.path.isdir(_target_dir + _target):
            _start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
            print(f'<< {_target} protocol [{_start_time}]>>')
            _protocol_name = _target
            _protocol_dir = _target_dir + _target
            _protocol_xml = _target_dir + _target + '/' + _target + '.xml'
            prime()
        else:
            continue

