import requests
import time
import logging

logger = logging.getLogger("API")
logging.basicConfig(format='[%(name)s]\t%(levelname)s\t%(message)s', level=logging.INFO)

#This class serves to handle all API requests to OpenSkyNetwork servers
#Requests data within a specified bounding box
#Delays requests until (server side) time limit has exceeded to prevent spamming
#Elsewhere you can pull the latest state data out and use it however you want
class APIController(object):
    def __init__(self):
        self.last_states = None
        self.last_time = 0
        self.last_req = 0
        self.url = "https://opensky-network.org/api/states/all"
        self.params = {"lamin":-90 , "lamax":90,
                        "lomin":-180, "lomax":180}

    def get_response(self):
        if self.last_time:
            if (time.time() - self.last_req) < 10:
                return False
        try:
            req = requests.get(self.url, params=self.params, timeout = 5)
            if req.status_code == 200:
                self.last_states = req.json().get('states')
                self.last_time = req.json().get('time')
                self.last_req = time.time()
                return True
            elif req.status_code == 429:
                logger.critical("HTTP Status 429: Exceeded request limit")
            else:
                logger.warning(f"API request failed with status {req.status_code}")
        except requests.exceptions.Timeout:
            logger.warning("API request timed out (More than 5s to respond)")
        return False

    def get_update(self):
            if self.get_response():
                return self.last_states
            return False

    def __str__(self):
        if self.last_states:
            for craft in self.last_states:
                if len(craft) > 17:
                    print(craft[1], end='\t')
            return ""
        else:
            return 'None'

    def set_bbox(self, latlo, lathi, lonlo, lonhi):
        self.params = {"lamin":latlo , "lamax":lathi,
                        "lomin":lonlo, "lomax":lonhi}
        logger.info(f"LatMin {latlo} LatMax {lathi} LonMin {lonlo} LonMax {lonhi}")

