from opensky_api import OpenSkyApi
from geographiclib.geodesic import Geodesic
import serial
import threading
import time
from random import random
import math
import configparser


#Angus, ON, CA
#me = (44.32236, -79.86168) #lat1 lon1

#Kaneville, IL, US
me = (41.83419, -88.53227) #lat1 lon1

#Earth geodesic used for all calculations
geod = Geodesic.WGS84

#Hanger holds info of all the aircraft. Right now collects everything.
#TODO: Make helper functions like counts, closest, in-view, etc
#TODO: Filter out crafts with no callsigns, on ground, too old, etc
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
                    if craft.callsign:
                        print(f"{craft.callsign}", end = "") 
                print('')


#Handles HTTP requests to server
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
    
    #Setup bounding box around "me" position
    trackingDist = 15  #kms
    g2 = geod.Direct(me[0],me[1],315,trackingDist*1000)
    g1 = geod.Direct(me[0],me[1],135,trackingDist*1000)
    area = (g1['lat2'], g2['lat2'], g2['lon2'], g1['lon2'])
    print(area)
    #Infinite loop checking for new data
    while(True):
        try:
            s = api.get_states(bbox = area)
            if s:
                hanger.new_data(s.states)
                print(f"New data with {len(s.states)} craft(s)")
            else:
                time.sleep(0.1)
        except Exception as e:
            print(e)
            return None
    
    
#Finds closest craft and points to it 
#TODO: make this JUST handle tracking commands held ... somewhere.
def SerialFunction(hanger):
    try:
        ardi = serial.Serial(port='COM3', baudrate=74880, timeout=.1)
    except serial.SerialException:
        print("COM Port cannot be opened")
        return None
    print("Waiting for board")
    while True:
        resp = ardi.read_until('\r\n',5)
        if resp[:5].decode("utf-8") == 'READY':
            break;
    print("COM Port open!")
    time.sleep(5)
    geod = Geodesic.WGS84
    
    #Infinite loop sending motor commands.
    while(True):
        if hanger.data:
            with hanger._lock:
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
                #print(trackingCraft)
                for craft in hanger.data:
                    if craft.icao24 == trackingCraft:
                        #print("Tracking")
                        newLatLon = geod.Direct(craft.latitude, craft.longitude, craft.true_track, craft.velocity*(time.time()-craft.time_position))
                        measure = geod.Inverse(me[0], me[1], newLatLon.get('lat2'), newLatLon.get('lon2'))
                        #Prioritze geo altitude over baro. Default to 45deg.
                        
                        alt = 45
                        if craft.geo_altitude:
                            elevation = math.degrees(math.atan(craft.geo_altitude/measure.get('s12')))           
                            alt = craft.geo_altitude
                        elif craft.baro_altitude:
                            elevation = math.degrees(math.atan(craft.baro_altitude/measure.get('s12')))
                            alt = craft.baro_altitude
                        print(f"{craft.callsign}\n\tDistance:\t{measure.get('s12')//1}\tAltitude:\t{alt//1}   \n\tAzimuth:\t{measure.get('azi1')//1} \tElevation:\t{elevation//1}")
                        break          
                if measure:
                    ardi.reset_output_buffer()
                    ardi.reset_input_buffer() 
                    ardi.write(angle_to_hex(measure.get('azi1')).to_bytes(2,byteorder='big'))
                    ardi.write(angle_to_hex(elevation).to_bytes(2,byteorder='big'))
                    #print(angle_to_hex(measure.get('azi1')).to_bytes(2,byteorder='big'),end='')
                    #print(angle_to_hex(elevation).to_bytes(2,byteorder='big'))
            time.sleep(0.25)
    
def angle_to_hex(ang):
    return int((ang%360)/0.015)


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    hanger = AircraftHanger()
    
    try:
        apiThread = threading.Thread(target=APIFunction, daemon=True,\
        kwargs={'hanger':hanger, 'user':config['OpenSkyAPI']['username'],'pw':config['OpenSkyAPI']['password']})
    except KeyError:
        print("No credentials for API")
        apiThread = threading.Thread(target=APIFunction, daemon=True, kwargs={'hanger':hanger})
    apiThread.start()
    
    serThread = threading.Thread(target=SerialFunction, daemon=True, args=(hanger, ))
    serThread.start()

    print("Starting display routine")
    while True:
        hanger.print_data()    
        time.sleep(5)
        
    print('Bye!')
    ardi.close()

