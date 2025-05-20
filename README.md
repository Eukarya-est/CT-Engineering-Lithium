# lithium
## XML for 'Auto Test for Reliability' Information Extractor 

XML for 'Auto Test for Reliability'. contains test description and parameters \
So this script for extracting XML to arrange and translate test description and parameters.

# Component
1. atrinfo-txt.py
2. target/
3. README.md
4. json/searchKey.json
5. json/jsonMap.json

# How to Use
1. Input a StarProtocol directory to target
    - Ex) 'ATR_Z1_40mm'
        - /target/ATR_Z1_40mm
        - /target/ATR_Z1_40mm/ATR_Z1_40mm.xml
        - /target/ATR_Z1_40mm/Site/3-18-22-1647575799540
        - /target/ATR_Z1_40mm/Site/3-18-22-1647575799540/session.xml
        - /target/ATR_Z1_40mm/Site/3-18-22-1647575799540/UIRx.xml

2. exeute the script
```shell
    python3 atrinfo-txt.py 
```
3. Get the result txt file
    - Ex) ATR_Z1_40mm.txt

2025.05.13 - 05.19


