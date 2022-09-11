from collections import deque
from time import time
from threading import Lock


class Airspace(object):

    def __init__(self):
        self.crafts = []
        self._lock = Lock()

    def setBase(self, coords):
        pass

    def getNearest(self):
        pass

    def updateSpace(self, vectors):
        with self._lock:
            for vect in vectors:
                flag_new = True
                for craft in self.crafts:
                    if vect[0] == craft.ICAO:
                        craft.updateStates(vect)
                        flag_new = False
                        break
                if flag_new:
                    self.crafts.append(Aircraft(vect))

    def getHeading(self, vector):
        pass

    def printSpace(self):
        print("Space")

    def countInFlight(self):
        pass


class Aircraft(object):
    position_history = 5
    
    def __init__(self, vector):
        #Deque to hold time, lat, lon, alt, speed, track, vert_rate
        self._positions = deque(maxlen=self.position_history)
        self.updateStates(vector)
        
    def __str__(self):
        return self.callsign
        
    def currentGPSCoords(self):
        #Must consider how to extrapolate. 
        #speed is groundspeed so must account for altitude
        return self._positions[-1][1:3]

    def lastGPSCoords(self):
        return self._positions

    def updateStates(self, vector):
        self.ICAO = vector[0]
        self.callsign = vector[1] if vector[1]!="" else " NOSIGN "
        self.country = vector[2] if vector[2] else " NOCOUNTRY "
        self.in_flight = True if vector[8]==0 else False
        self._positions.append((vector[3],vector[6], vector[5], 
                self.fuseAltitudes(vector[13], vector[7]), 
                vector[9], vector[10], vector[11]))
        return None    

    def fuseAltitudes(self, geo, baro):
        if geo:
            if baro: 
                #Need to fuse them somehow
                return (geo+baro)/2
            else:  
                return geo
        else: 
            return baro if baro else 0