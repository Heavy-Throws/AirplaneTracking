from geographiclib.geodesic import Geodesic
from collections import deque
import serial
import threading
import time
import math
import configparser
import logging
from opensky_api import OpenSkyApi
import Aircraft

logger_main = logging.getLogger("MAIN")
logging.basicConfig(format='[%(levelname)s]\t%(message)s', level=logging.INFO)
logger_main.setLevel(logging.DEBUG)

#Angus, ON, CA
#me = (44.32236, -79.86168) #lat1 lon1

#Kaneville, IL, US
#me = (41.83419, -88.53227) #lat1 lon1

#Vaughan, ON, CA
#me = (43.78281, -79.53771) 

#Scotch Block, ON, CA
me = (43.56826, -79.96056) 

#Earth geodesic used for all calculations
geod = Geodesic.WGS84

class Aircraft(object):
    position_history = 5
    
    def __init__(self, state_info):
        self._statehist = deque(maxlen=self.position_history)
        self._states = dict() #eventually get rid of this
        self._stale = False
        self._valid = True
        self._est_pos = (None, None, None)
        self.updateStates(state_info)
        
    def __str__(self):
        return self._statehist[-1].callsign
        
    def currentGPSCoords(self):
        #Do ground calculations then add altitude
        if self.is_stale():
            return None
        if self._statehist[-1].true_track is None:
            return None
        if self._statehist[-1].baro_altitude is None:
            return None
        if self._statehist[-1].velocity is None:
            return (self._statehist[-1].latitude, self._statehist[-1].longitude, self._statehist[-1].baro_altitude)
        alt = self._statehist[-1].baro_altitude
        time_diff = time.time() - self._statehist[-1].time_position
        ground_location = geod.Direct(self._statehist[-1].latitude, self._statehist[-1].longitude,self._statehist[-1].true_track, self._statehist[-1].velocity*time_diff)
        if self._statehist[-1].vertical_rate is not None:
            alt = alt + self._statehist[-1].vertical_rate * time_diff
        self._est_pos = (ground_location['lat2'],ground_location['lon2'], alt)
        return self._est_pos

    def updateStates(self, state_info):
        self._statehist.append(state_info)
        self._states = state_info
        if self._statehist[-1].callsign is None or self._statehist[-1].callsign == "        ":
            self._statehist[-1].callsign = "--------"

    def icao(self):
        return self._statehist[-1].icao24

    def is_usable(self): 
        if not self.is_stale():
            if self.is_valid():
                if self._statehist[-1].baro_altitude is not None:
                    if self._statehist[-1].true_track is not None:
                        return True
        return False


    def is_stale(self, max_time = 30):
        if (self._statehist[-1].time_position is None) or (time.time() - self._statehist[-1].time_position > max_time):
            self._stale = True
        else:
            self._stale = False
        return self._stale
    
    def is_valid(self, alt_lo=0, alt_hi=55000, filterOnGround = False):
        if (self._statehist[-1].baro_altitude is not None) and (self._statehist[-1].on_ground is not None):
            if self._statehist[-1].baro_altitude < alt_lo:
                self._valid = False
            elif self._statehist[-1].baro_altitude > alt_hi:
                self._valid = False
            elif filterOnGround and self._statehist[-1].on_ground:
                self._valid = False
            else:
                self._valid = True
        else: 
            self._valid = False
        return self._valid


#New version, make it better!
class Airspace(object):
    def __init__(self, vectors = None ):
        self._lock = threading.Lock()
        self._craftData = {}
        self._me = me
        if vectors:
            for craft in vectors:
                self._craftData[craft.icao24] = Aircraft(craft)

    def listAll(self):
        with self._lock:
            if len(self._craftData)>0:
                print("\n\n\nCALL    \tLAT     \tLONG     \tALT    \tDIST")
            for craft in self._craftData.values():
                if craft.is_valid():
                    if not craft.is_stale():
                        data = craft.currentGPSCoords()
                        print(f"{craft}\t{data[0]:.5f}\t{data[1]:.5f}\t{data[2]:.0f}\t{self.getDistance(craft.icao()):.0f}")

    def updateMe(self, loc):
        self._me = loc

    def updateStates(self, vectors):
        with self._lock:
            for craft in vectors:
                if craft.icao24 in self._craftData:
                    self._craftData[craft.icao24].updateStates(craft)
                else:
                    self._craftData[craft.icao24] = Aircraft(craft)

    def getDistance(self, craft): #Must be icao 
        lat1, lon1, alt1 = craft.currentGPSCoords()
        lat2, lon2, alt2 = me[0], me[1], 0
        g1 = geod.Inverse(lat1, lon1, lat2, lon2)
        dist = math.sqrt(g1['s12']**2 + alt1**2)
        return dist

    def getCount(self, alt_lo=0, alt_hi=55000, filterOnGround = False):
        count = 0
        with self._lock:
            for craft in self._craftData.values():
                if not craft.is_stale():
                    if craft.is_valid(alt_lo, alt_hi, filterOnGround):
                        count += 1
        return count

    def getClosest(self, alt_min = 0):
        if self.getCount() > 0:
            target = None
            target_dist = None
            with self._lock:
                for craft in self._craftData.values():
                    if craft.is_usable() and craft.is_valid(alt_lo=alt_min):
                        if target is None:
                            target = craft 
                            target_dist = self.getDistance(target) #BROKEN???
                            logger_main.debug(f"target {target} is {target_dist}")
                        elif self.getDistance(craft) < target_dist:
                            target = craft 
                            target_dist = self.getDistance(target)
                            logger_main.debug(f"target {target} is {target_dist}")
            return target
        else:
            return None

#Handles HTTP requests to server
def APIFunction(airspace, user=None, pw=None):
    try:
        if user and pw:
            api = OpenSkyApi(username = user, password=pw)
        else:
            api = OpenSkyApi()
    except Exception as e:
        logger_main.critical(f"API not responding {e}")
        return None
        
    logger_main.info("API active")
    
    #Setup bounding box around "me" position
    trackingDist = 75  #kms
    g2 = geod.Direct(me[0],me[1],315,trackingDist*1000)
    g1 = geod.Direct(me[0],me[1],135,trackingDist*1000)
    area = (g1['lat2'], g2['lat2'], g2['lon2'], g1['lon2'])
    logger_main.debug(area)
    #Infinite loop checking for new data
    while(True):
        try:
            s = api.get_states(bbox=area)
            if s:
                airspace.updateStates(s.states)
                logger_main.info(f"New data with {len(s.states)} craft(s)")
            else:
                time.sleep(0.1)
        except Exception as e:
            logger_main.warning(e)
            return None
    
    
#Finds closest craft and points to it 
#TODO: make this JUST handle tracking commands held ... somewhere.
def SerialFunction(airspace):
    try:
        ardi = serial.Serial(port='COM3', baudrate=74880, timeout=.5)
    except serial.SerialException:
        logger_main.warning("COM Port cannot be opened")
        return None
    logger_main.info("Waiting for board")
    while True:
        resp = ardi.read_until('\r\n',5)
        if resp[:5].decode("utf-8") == 'READY':
            break;
    logger_main.info("COM Port open!")
    time.sleep(5)
    geod = Geodesic.WGS84
    return None
    #Infinite loop sending motor commands.
    # while(True):
    #     if airspace.data:
    #         with airspace._lock:
    #             trackingCraft = ''
    #             closestdist = 999999
    #             for craft in airspace.data:
    #                 if (time.time()//1-craft.time_position < 20 and craft.on_ground == False):
    #                     measure = geod.Inverse(me[0], me[1], craft.latitude, craft.longitude)
    #                     logger_main.debug(f"{craft.callsign} {measure.get('s12')}")
    #                     if measure.get('s12') < closestdist:
    #                         trackingCraft = craft.icao24
    #                         closestdist = measure.get('s12')
    #             elevation = 45
    #             logger_main.debug(trackingCraft)
    #             for craft in airspace.data:
    #                 if craft.icao24 == trackingCraft:
    #                     logger_main.info("Tracking")
    #                     newLatLon = geod.Direct(craft.latitude, craft.longitude, craft.true_track, craft.velocity*(time.time()-craft.time_position))
    #                     measure = geod.Inverse(me[0], me[1], newLatLon.get('lat2'), newLatLon.get('lon2'))
    #                     #Prioritze geo altitude over baro. Default to 45deg.     
    #                     alt = 45
    #                     if craft.geo_altitude:
    #                         elevation = math.degrees(math.atan(craft.geo_altitude/measure.get('s12')))           
    #                         alt = craft.geo_altitude
    #                     elif craft.baro_altitude:
    #                         elevation = math.degrees(math.atan(craft.baro_altitude/measure.get('s12')))
    #                         alt = craft.baro_altitude
    #                     logger_main.info(f"{craft.callsign}\n\tDistance:\t{measure.get('s12')//1}\tAltitude:\t{alt//1}   \n\tAzimuth:\t{measure.get('azi1')//1} \tElevation:\t{elevation//1}")
    #                     break          
    #             if measure:
    #                 #SHIP IT
    #                 data = ((angle_to_hex(measure.get('azi1'))<<16) + angle_to_hex(elevation)).to_bytes(4,byteorder='big')
    #                 ardi.write(data)
    #         time.sleep(0.2)
    
def angle_to_hex(ang):
    return int((ang%360)/0.015)


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('config.ini')
    

    airspace = Airspace()
    logger_main.debug("YOU ARE IN DEBUG LOGGER MODE")
    try:
        apiThread = threading.Thread(target=APIFunction, daemon=True,\
        kwargs={'airspace':airspace, 'user':config['OpenSkyAPI']['username'],'pw':config['OpenSkyAPI']['password']})                            
    except KeyError:
        logger_main.info("No credentials for API")
        apiThread = threading.Thread(target=APIFunction, daemon=True, kwargs={'airspace':airspace})
    apiThread.start()
    
    serThread = threading.Thread(target=SerialFunction, daemon=True, args=(airspace, ))
    serThread.start()

    logger_main.info("Starting display routine")
    while True:
        time.sleep(5)
        numCraft = airspace.getCount()
        print(f"{numCraft} valid units being tracked.")  
        if numCraft > 0:
            a = airspace.getClosest(500)
            logger_main.info(f"{a} is closest")
        
    logger_main.debug('Bye!')
    ardi.close()

