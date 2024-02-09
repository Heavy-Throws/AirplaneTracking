from opensky_api import OpenSkyApi, StateVector
from geographiclib.geodesic import Geodesic
from collections import deque
import serial
import threading
import time
from random import random
import math
import configparser
import logging

#[StateVector(dict_values(['c07b0a', 'ACA746  ', 'Canada', 1707134629, 1707134629, -79.9225, 43.4983, 1432.56, False, 108.31, 57.22, -4.23, None, 1386.84, '3266', False, 0])), StateVector(dict_values(['c073ea', 'CGRXH   ', 'Canada', 1707134629, 1707134629, -79.7719, 43.7152, 1676.4, False, 120.45, 226.56, -7.8, None, 1623.06, '7136', False, 0])), StateVector(dict_values(['c056c6', 'WJA375  ', 'Canada', 1707134629, 1707134629, -79.8448, 43.6643, 2407.92, False, 135, 226.39, -4.88, None, 2362.2, '0664', False, 0])), StateVector(dict_values(['c03af2', 'WJA652  ', 'Canada', 1707134629, 1707134629, -79.7827, 43.5924, 876.3, False, 86.34, 48.14, -1.95, None, 845.82, '3377', False, 0]))]


logger_main = logging.getLogger("MAIN")
logging.basicConfig(format='[%(levelname)s]\t%(message)s', level=logging.INFO)

#Scotch Block, ON, CA
me = (43.56826, -79.96056) 

#Earth geodesic used for all calculations
geod = Geodesic.WGS84

svl = [StateVector(['c07b0a', 'ACA746  ', 'Canada', 1707134629, 1707134629, -79.9225, 43.4983, 1432.56, False, 108.31, 57.22, -4.23, None, 1386.84, '3266', False, 0]), 
       StateVector(['c073ea', 'CGRXH   ', 'Canada', 1707134629, 1707134629, -79.7719, 43.7152, 1676.4, False, 120.45, 226.56, -7.8, None, 1623.06, '7136', False, 0]), 
       StateVector(['c056c6', 'WJA375  ', 'Canada', 1707134629, 1707134629, -79.8448, 43.6643, 2407.92, False, 135, 226.39, -4.88, None, 2362.2, '0664', False, 0]), 
       StateVector(['c03af2', 'WJA652  ', 'Canada', 1707134629, 1707134629, -79.7827, 43.5924, 876.3, False, 86.34, 48.14, -1.95, None, 845.82, '3377', False, 0])]

sv2 = [StateVector(['b07b0a', 'ACA777  ', 'Canada', 1707134634, 1707134634, -79.9999, 43.4999, 1432.56, False, 108.31, 57.22, -4.23, None, 1386.84, '3266', False, 0]), 
       StateVector(['c073ea', 'CGRXH   ', 'Canada', 1707134634, 1707134634, -79.7888, 43.7222, 1676.4, False, 120.45, 226.56, -7.8, None, 1623.06, '7136', False, 0]), 
       StateVector(['c056c6', 'WJA375  ', 'Canada', 1707134634, 1707134634, -79.8555, 43.6777, 2407.92, False, 135, 226.39, -4.88, None, 2362.2, '0664', False, 0]), 
       StateVector(['c03af2', 'WJA652  ', 'Canada', 1707134634, 1707134634, -79.7888, 43.6000, 876.3, False, 86.34, 48.14, -1.95, None, 845.82, '3377', False, 0])]
test_time = 1707134632.215


class Aircraft(object):
    position_history = 5
    
    def __init__(self, state_info):
        self._states = dict()
        self._stale = False
        self._valid = True
        self._est_pos = (None, None, None)
        self.updateStates(state_info)
        print(f"Aircraft init {self._states.icao24}")
        
    def __str__(self):
        return self.callsign
        
    def currentGPSCoords(self):
        #Do ground calculations then add altitude
        self.check_stale()
        if self._states.true_track is None:
            return None
        if self._states.velocity is None:
            return None
        if self._states.baro_altitude is None:
            return None
        if self._stale:
            return None
        alt = self._states.baro_altitude
        time_diff = test_time - self._states.time_position  #DEBUG
        ground_location = geod.Direct(self._states.latitude, self._states.longitude,self._states.true_track, self._states.velocity*time_diff)
        if self._states.vertical_rate is not None:
            alt = alt + self._states.vertical_rate * time_diff
        self._est_pos = (ground_location['lat2'],ground_location['lon2'], alt)
        return self._est_pos, self._states.time_position

    def updateStates(self, state_info):
        self._states = state_info

    def icao(self):
        return self._states.icao24

    def check_stale(self):
        #if time.time() - self._states.time_position > 20:
        if test_time - self._states.time_position > 7:
            self._stale = True
        else:
            self._stale = False
        return self._stale


class Airspace(object):
    def __init__(self, vectors):
        self._craftData = {}
        self._me = me
        for craft in vectors:
            self._craftData[craft.icao24] = Aircraft(craft)

    def listAll(self):
        for craft in self._craftData.values():
            data = craft.currentGPSCoords() 
            if data:
                print(data)

    def updateMe(self, loc):
        self._me = loc

    def updateStates(self, vectors):
        for craft in vectors:
            if craft.icao24 in self._craftData:
                self._craftData[craft.icao24].updateStates(craft)
            else:
                self._craftData[craft.icao24] = Aircraft(craft)

a = Airspace(svl)
a.listAll()
a.updateStates(sv2)
test_time += 5
a.listAll()