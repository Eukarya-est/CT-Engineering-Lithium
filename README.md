# CT-Engineering Lithium
## XML for 'Auto Test for Reliability' Information Extractor 

XML for 'Auto Test for Reliability'. contains test description and parameters \
So this script for extracting XML to arrange and translate test description and parameters.

## Component
1. atrinfo-txt.py
2. target/
3. README.md
4. json/searchKey.json
    - The list of Scan settings to search
5. json/jsonMap.json
    - The map of Scan setting key and key dictionary json file(enum-*.json)
6. json/enum-*.json
    - The key dictionary

## How to Use
1. Input a StarProtocol directory to target; Star Protocolのフォルダを'target'フォルダに入れる。
    - Ex) 'ATR_Z1_40mm'
        - /target/ATR_Z1_40mm
        - /target/ATR_Z1_40mm/ATR_Z1_40mm.xml
        - /target/ATR_Z1_40mm/Site/3-18-22-1647575799540
        - /target/ATR_Z1_40mm/Site/3-18-22-1647575799540/session.xml
        - /target/ATR_Z1_40mm/Site/3-18-22-1647575799540/UIRx.xml

2. exeute the script; 'starinfo-txt.py'を実行する。
```shell
    python3 atrinfo-txt.py 
```
3. Get the result txt file； 結果ファイルを得る。
    - Ex) ATR_Z1_40mm.txt

* It has some differences from real work thing.

2025.05.13 - 05.19




