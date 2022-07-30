from opensky_api import OpenSkyApi
from geographiclib.geodesic import Geodesic
import serial
import threading
import time
from random import random
import math
import configparser

#area = (44.04015, 44.59059, -80.26549, -79.45082) #lat1 lat2 lon1 long2
#me = (44.32236, -79.86168) #lat1 lon1

area = (41.05668, 42.55962, -89.53224, -87.69588) #lat1 lat2 lon1 long2
me = (41.83419, -88.53227) #lat1 lon1




class AircraftHanger:
    def __init__(self):
        self.data = None
        self.closest = None
        self._lock = threading.Lock()
    
    def new_data(self, newData):
        with self._lock:
            self.data = newData
        
    def estimate_pos(self, ID):
        with self._lock:
            return None
        
    def print_data(self):
        with self._lock:
            if self.data:
                for craft in self.data:
                    print(f"{craft.callsign}", end = "")

def APIFunction(hanger, user=None, pw=None):
    try:
        if user and pw:
            api = OpenSkyApi(username = user, password=pw)
        else:
            api = OpenSkyApi()
    except Exception as e:
        print(f"API not responding {e}")
        return None
    print("API active")
    while(True):
        try:
            s = api.get_states(bbox = area)
            if s:
                hanger.new_data(s.states)
                print("New data")
            else:
                time.sleep(0.1)
        except Exception as e:
            print(e)
            return None
    
    
def SerialFunction(hanger):
    try:
        ardi = serial.Serial(port='COM3', baudrate=74880, timeout=.1)
    except serial.SerialException:
        print("COM Port cannot be opened")
        return None
    while True:
        resp = ardi.read_until('\r\n',5)
        if resp[:5].decode("utf-8") == 'READY':
            break;
    print("COM Port open!")
    geod = Geodesic.WGS84
    while(True):
        if hanger.data:
            trackingCraft = ''
            closestdist = 999999
            for craft in hanger.data:
                if (time.time()//1-craft.time_position < 20 and craft.on_ground == False):
                    measure = geod.Inverse(me[0], me[1], craft.latitude, craft.longitude)
                    #print(f"{craft.callsign} {measure.get('s12')}")
                    if measure.get('s12') < closestdist:
                        trackingCraft = craft.icao24
                        closestdist = measure.get('s12')
            elevation = 45
            for craft in hanger.data:
                if craft.icao24 == trackingCraft:
                    newLatLon = geod.Direct(craft.latitude, craft.longitude, craft.true_track, craft.velocity*(time.time()-craft.time_position))
                    #print(newLatLon, end="    <------")
                    measure = geod.Inverse(me[0], me[1], newLatLon.get('lat2'), newLatLon.get('lon2'))
                    #Prioritze geo altitude over baro. Default to 45deg.
                    
                    alt = None
                    if craft.geo_altitude:
                        elevation = math.degrees(math.atan(craft.geo_altitude/measure.get('s12')))           
                        alt = craft.geo_altitude
                    elif craft.baro_altitude:
                        elevation = math.degrees(math.atan(craft.baro_altitude/measure.get('s12')))
                        alt = craft.baro_altitude
                    #print(f"\tDistance:\t{measure.get('s12')//1} \n\tAltitude:\t{alt//1}   \n\tAzimuth:\t{measure.get('azi1')//1}    \n\tElevation:\t{elevation//1}")
                    break
                        
            ardi.reset_output_buffer()
            ardi.reset_input_buffer() 
            ardi.write(angle_to_hex(measure.get('azi1')).to_bytes(2,byteorder='big'))
            ardi.write(angle_to_hex(elevation).to_bytes(2,byteorder='big'))
            time.sleep(0.1)
    
def angle_to_hex(ang):
    return int((ang%360)/0.015)

if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    hanger = AircraftHanger()
    try:
        apiThread = threading.Thread(target=APIFunction, daemon=True, kwargs={'hanger':hanger,\
                                                                            'user':config['OpenSkyAPI']['username'],\
                                                                            'pw':config['OpenSkyAPI']['password']})
    except KeyError:
        print("No credentials for API")
        apiThread = threading.Thread(target=APIFunction, daemon=True, kwargs={'hanger':hanger})
    apiThread.start()
    
    serThread = threading.Thread(target=SerialFunction, daemon=True, args=(hanger, ))
    serThread.start()

    while True:
        hanger.print_data()    
        time.sleep(5)
        
    print('Bye!')
    ardi.close()

