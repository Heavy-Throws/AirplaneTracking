from geographiclib.geodesic import Geodesic
import serial
import threading
import time
import configparser
import logging
from opensky_api import OpenSkyApi
from Open_Airspace import Aircraft, Airspace

logger_main = logging.getLogger("MAIN")
logging.basicConfig(format='[%(levelname)s]\t%(message)s', level=logging.INFO)
logger_main.setLevel(logging.DEBUG)

#Scotch Block, ON, CA
me = (43.56826, -79.96056) 

#Earth geodesic used for all calculations
geod = Geodesic.WGS84



#Handles HTTP requests to server
def APIFunction(airspace, user=None, pw=None):
    try:
        if user and pw:
            api = OpenSkyApi(username = user, password=pw)
            logger_main.debug(f"Logged in as {user}")
        else:
            api = OpenSkyApi()
    except Exception as e:
        logger_main.critical(f"API not responding {e}")
        return None
        
    logger_main.info("API active")
    
    #Setup bounding box around "me" position
    logger_main.debug(airspace.get_bbox())
    #Infinite loop checking for new data
    while(True):
        try:
            s = api.get_states(bbox=airspace.get_bbox())
            if s:
                airspace.updateStates(s.states)
                logger_main.debug(f"New data with {len(s.states)} craft(s)")
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
    

    airspace = Airspace(center=me)
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
        if numCraft > 0:
            a = airspace.getClosest(500)
            logger_main.info(f"{numCraft} valid units being tracked and {a} is closest")
        
    ardi.close()

