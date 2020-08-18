#!/usr/bin/env python3
# -*- coding: utf8 -*-
"""
Script to download election forecasts from 538
and PredictIt and then diff them.
"""

import sys
import os
import traceback
import argparse
import time
import logging
import csv
import requests
import re
import json

from io import BytesIO
from zipfile import ZipFile
from urllib.request import urlopen
from collections import Counter 


FIVE38_CSV_URL = 'https://projects.fivethirtyeight.com/2020-general-data/presidential_state_toplines_2020.csv'
PREDICTIT_XML_URL = 'https://www.predictit.org/api/marketdata/all/'

"""
Gets a map of state names and Trumps victory odds in those states
"""
def get538Data():
    with requests.Session() as s:
        download = s.get(FIVE38_CSV_URL)

        decoded_content = download.content.decode('utf-8')

        cr = csv.reader(decoded_content.splitlines(), delimiter=',')
        next(cr, None)  # skip the headers
        stateDict = { row[7]: float(row[10]) for row in cr }
    
    log.debug(stateDict)
    return stateDict

def getPredictItData():
    predictItData = {}
    with requests.Session() as s:
        download = s.get(PREDICTIT_XML_URL)
        data = json.loads(download.content)

        for market in data["markets"]:
            marketName = market["name"]
            if re.match("Which party will win .* in the +2020 presidential election.*", marketName):
                stateName = re.findall('(win )(.+)(?= in)', marketName)[0][1]
                #538 doesn't use leading 0s, drop them
                if re.match("[A-Z][A-Z]\-0[0-9]", stateName):
                    stateName = stateName[:3] + stateName[4:]
                # Unabreviate DC
                if stateName == "DC":
                    stateName = "District of Colombia"
                
                # Get the odds and store them
                for contract in market["contracts"]:
                    if contract["name"] == "Republican":
                        predictItData[stateName] = float(contract["lastTradePrice"])
    
    log.debug(predictItData)
    return predictItData


def main(args):
    five38Data = get538Data()
    predictItData = getPredictItData()

    diffs = {key: five38Data[key] - predictItData.get(key, 0) for key in five38Data}
    absDiffs = {key: abs(five38Data[key] - predictItData.get(key, 0)) for key in five38Data}

    diffCounter = Counter(absDiffs) 

    print("All Diffs: \n", diffs, "\n\n")
    high = diffCounter.most_common(5)
    highest = [{state[0]: diffs[state[0]]} for state in high]
    print("Highest 5: \n", highest, "\n")

    return


# create file handler which logs even debug messages
log = logging.getLogger()
log.setLevel(logging.ERROR)  # DEBUG | INFO | WARNING | ERROR | CRITICAL
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - Line: %(lineno)d\n%(message)s')
sh = logging.StreamHandler()
sh.setLevel(logging.ERROR)
sh.setFormatter(formatter)
log.addHandler(sh)
fh = logging.FileHandler(os.path.abspath(os.path.join(
    os.path.dirname(__file__), 
    os.path.basename(__file__).rstrip('.py') + '.log'
)))
fh.setLevel(logging.ERROR)
fh.setFormatter(formatter)
log.addHandler(fh)

if __name__ == '__main__':
    try:
        start_time = time.time()
        # Parser: See http://docs.python.org/dev/library/argparse.html
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('-v', '--verbose', action='store_true', default=False, help='verbose output')
        parser.add_argument('-ver', '--version', action='version', version='0.0.1')
        parser.add_argument('-d', '--directory', action='store_const', default=".", const=dir, help="directory to store data in")
        args = parser.parse_args()
        if args.verbose:
            fh.setLevel(logging.DEBUG)
            log.setLevel(logging.DEBUG)
        log.info("%s Started" % parser.prog)
        main(args)
        log.info("%s Ended" % parser.prog)
        log.info("Total running time in seconds: %0.2f" % (time.time() - start_time))
        sys.exit(0)
    except KeyboardInterrupt as e:  # Ctrl-C
        raise e
    except SystemExit as e:  # sys.exit()
        raise e
    except Exception as e:
        print('ERROR, UNEXPECTED EXCEPTION')
        print(str(e))
        traceback.print_exc()
        os._exit(1)