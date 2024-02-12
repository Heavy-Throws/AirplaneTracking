import math
import time
import threading
import logging
from collections import deque
from geographiclib.geodesic import Geodesic

#Earth geodesic used for all calculations
geod = Geodesic.WGS84
logger_space = logging.getLogger("RADAR")

#Generic container used for state estimations and historical data. 
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





#Holds record of all crafts. 
#Calculates distance, az/al
#Defaults to CYYZ tower with 75km range. 
class Airspace(object):
    def __init__(self, vectors = None, center = (43.67509, -79.62930), radius = 75):
        self._lock = threading.Lock()
        self._live = True
        self._craftData = {}
        self._trackingDist = radius
        self._bbox = None
        self.updateFocus(center)
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

    def get_trackingDist(self):
        return self._trackingDist
    
    def set_trackingDist(self, val):
        if val < 1 or val > 250:
            raise ValueError("Tracking radius must be between 1km and 250km")
        else:
            self._trackingDist = val
            self.set_bbox()

    def get_focus(self):
        return self._focus

    def updateFocus(self, loc):
        if loc is not None:
            self._focus = loc
            self.set_bbox()
            self._live = True
        else:
            self._live = False

    def set_bbox(self):
        if self._live:
            g2 = geod.Direct(self._focus[0],self._focus[1],315,self._trackingDist*1000)
            g1 = geod.Direct(self._focus[0],self._focus[1],135,self._trackingDist*1000)
            self._bbox = (g1['lat2'], g2['lat2'], g2['lon2'], g1['lon2'])

    def get_bbox(self):
        return self._bbox

    def updateStates(self, vectors):
        with self._lock:
            for craft in vectors:
                if craft.icao24 in self._craftData:
                    self._craftData[craft.icao24].updateStates(craft)
                else:
                    self._craftData[craft.icao24] = Aircraft(craft)

    def getDistance(self, craft): #Must be icao 
        if self._live:
            lat1, lon1, alt1 = craft.currentGPSCoords()
            lat2, lon2, alt2 = self._focus[0], self._focus[1], 0
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
                        elif self.getDistance(craft) < target_dist:
                            target = craft 
                            target_dist = self.getDistance(target)
            return target
        else:
            return None
    
    def getVectors(self, craft):
        pass
    