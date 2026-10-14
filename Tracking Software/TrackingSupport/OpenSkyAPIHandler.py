#Standard libraries
import logging
import time
import sys
import threading
from queue import Queue

#Custom libraries
from geographiclib.geodesic import Geodesic
from opensky_api import OpenSkyApi, TokenManager

logger_api = logging.getLogger("Tracker.api") 
geod_api = Geodesic.WGS84

class Flight_API(object):
    def __init__(self, base = (43.677, -79.631), radius = 20000):
        self._source = "OpenSky API"
        self._start_time = int(time.time())
        self._stale = False
        self._valid = True  #Unused? 
        self._running = False

        self._radius = radius
        self._base = base
        self._trackingArea = 0
        self.setBase(base) #defaults to CYYZ

        self._data_queue = Queue(maxsize=25) #1min
        self._call_count = 0

    def __str__(self):
        return self._source

    def checkCoords(self, coords) -> bool:
        func = sys._getframe(1).f_code.co_name
        if len(coords) > 3 or len(coords) < 2: 
            logger_api.error(f"Incorrect number of arguements for {func} to handle. Should be (lat lon) or (lat lon alt)")
            return False
        if coords[0] < -90 or coords[0] > 90:
            logger_api.error(f"{func} LAT not valid, exceeds 90deg")
            return False
        if coords[1] < -180 or coords[1] > 180:
            logger_api.error(f"{func} LON not valid, exceeds 180deg")
            return False
        if len(coords) == 3:    #has alt
            if coords[2] < -100 or coords[2] > 10000:
                logger_api.error(f"{func} ALT not valid, too low or too high")
                return False
        return True

    def setRadius(self, radius):
        if radius <= 0: 
            logger_api.debug("setRadius invalid arguement. Not changed")
        else: 
            self._radius = radius
            logger_api.debug(f"Radius changed to {self._radius}")
            self.bboxCalc()

    def setBase(self, coords):
        #Confirm values are valid before doing anything else.
        #TODO: Should this correct values instead? lon%180? 
        if self.checkCoords(coords):
            self._base = coords
            logger_api.info(f"New coords for base are {self._base}")
            self.bboxCalc()
            return True
        return False

    def bboxCalc(self):
        #Sets radius to any positive number and warns user of token usage
        n = geod_api.Direct(self._base[0], self._base[1], 0, self._radius)
        e = geod_api.Direct(self._base[0], self._base[1], 90, self._radius)
        s = geod_api.Direct(self._base[0], self._base[1], 180, self._radius)
        w = geod_api.Direct(self._base[0], self._base[1], 270, self._radius)
        self._bbox = (s['lat2'], n['lat2'], w['lon2'], e['lon2'])
        logger_api.debug(f"New bbox is {self._bbox}")
        self._trackingArea = (self._bbox[1]-self._bbox[0]) * (self._bbox[3]-self._bbox[2])
        credits = 0
        if self._trackingArea > 400:
            credits = 4
        elif self._trackingArea > 100:
            credits = 3
        elif self._trackingArea > 25:
            credits = 2
        else: 
            credits = 1

        logger_api.info(f"New tracking area is {self._trackingArea} sq degrees, costing {credits} credits per call.")
        
    def start(self):
        #What checks need to be done before starting the thread? 
        if not self.checkCoords(self._base): #might not be needed? 
            return False
        try:
            apiThread = threading.Thread(target=self.apiThread, daemon=True,\
            kwargs={'data_queue':self._data_queue})                            
        except Exception as apiThreadErrorCode:
            logger_api.info(f"Failed to run API thread: {apiThreadErrorCode}")
        self._running = True 
        apiThread.start()    

    def stop(self):
        self._running = False

    #TODO: Error handling
    def apiThread(self, data_queue):
        try:
            api = OpenSkyApi(token_manager=TokenManager.from_json_file("credentials.json"))
        except Exception as e:
            logger_api.critical(f"API not responding {e}")
            return None    
        logger_api.info("API active")

        #Infinite loop checking for new data
        while(self._running):
            try:
                s = api.get_states(bbox=self._bbox)
                if s:
                    logger_api.debug(f"New data with {len(s.states)} craft(s)")
                    for item in s.states: 
                        item.callsign = str(item.callsign).strip()
                    data_queue.put(s.states)
                    self._call_count += 1
                else:
                    time.sleep(0.5)
            except Exception as e:
                logger_api.warning(e)
                return None
        return None
            
    def queue_size(self):
        return self._data_queue.qsize()

    def call_count(self):
        return self._call_count
    
    def pull_data(self):
        if self._data_queue.empty():
            return None
        else:
            return self._data_queue.get()

