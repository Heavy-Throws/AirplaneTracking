from geographiclib.geodesic import Geodesic
import serial
import threading
import time
import math
import configparser
import logging
import OpenSkyTracking
import Aircraft

logger_main = logging.getLogger("MAIN")
logging.basicConfig(format='[%(levelname)s]\t%(message)s', level=logging.INFO)

#Angus, ON, CA
#me = (44.32236, -79.86168) #lat1 lon1

#Kaneville, IL, US
#me = (41.83419, -88.53227) #lat1 lon1

#Vaughan, ON, CA
me = (43.78144, -79.54569)

#Earth geodesic used for all calculations
geod = Geodesic.WGS84

#Handles all airspace related queries
airspace = Aircraft.Airspace()

#Hanger holds info of all the aircraft. Right now collects everything.
#TODO: Make helper functions like counts, closest, in-view, etc
#TODO: Filter out crafts with no callsigns, on ground, too old, etc
#TODO: Conver hanger variable into Airspace namespace.


#Handles HTTP requests to server
def APIFunction(airspace, user=None, pw=None):

    api = OpenSkyTracking.APIController()     
    print("API active")
    
    #Setup bounding box around "me" position
    trackingDist = 15  #kms
    g2 = geod.Direct(me[0],me[1],315,trackingDist*1000)
    g1 = geod.Direct(me[0],me[1],135,trackingDist*1000)
    area = (g1['lat2'], g2['lat2'], g2['lon2'], g1['lon2'])

    api.set_bbox(area[0], area[1], area[2], area[3])
    #Infinite loop checking for new data
    while(True):
        try:
            s = api.get_update()
            if s:
                airspace.updateSpace(s)
                logger_main.info(f"New data with {len(s)} craft(s)")
            else:
                time.sleep(0.1)
        except Exception as e:
            logger_main.warning(e)
            return None
    
    
#Finds closest craft and points to it 
#TODO: make this JUST handle tracking commands held ... somewhere.
def SerialFunction(airspace):
    try:
        ardi = serial.Serial(port='COM3', baudrate=74880, timeout=.1)
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
    
    #Infinite loop sending motor commands.
    while(True):
        if airspace.data:
            with airspace._lock:
                trackingCraft = ''
                closestdist = 999999
                for craft in airspace.crafts:
                    if (time.time()//1-craft.time_position < 20 and craft.on_ground == False):
                        measure = geod.Inverse(me[0], me[1], craft.latitude, craft.longitude)
                        logger_main.debug(f"{craft.callsign} {measure.get('s12')}")
                        if measure.get('s12') < closestdist:
                            trackingCraft = craft.icao24
                            closestdist = measure.get('s12')
                elevation = 45
                logger_main.debug(trackingCraft)
                for craft in airspace.crafts:
                    if craft.icao24 == trackingCraft:
                        logger_main.info("Tracking")
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
                        logger_main.info(f"{craft.callsign}\n\tDistance:\t{measure.get('s12')//1}\tAltitude:\t{alt//1}   \n\tAzimuth:\t{measure.get('azi1')//1} \tElevation:\t{elevation//1}")
                        break          
                if measure:
                    ardi.reset_output_buffer()
                    ardi.reset_input_buffer() 
                    ardi.write(angle_to_hex(measure.get('azi1')).to_bytes(2,byteorder='big'))
                    ardi.write(angle_to_hex(elevation).to_bytes(2,byteorder='big'))
                    logger_main.debug(angle_to_hex(measure.get('azi1')).to_bytes(2,byteorder='big'),end='')
                    logger_main.debug(angle_to_hex(elevation).to_bytes(2,byteorder='big'))
            time.sleep(0.25)
    
def angle_to_hex(ang):
    return int((ang%360)/0.015)


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    try:
        apiThread = threading.Thread(target=APIFunction, daemon=True,\
        kwargs={'airspace':airspace, 'user':config['OpenSkyAPI']['username'],'pw':config['OpenSkyAPI']['password']})
    except KeyError:
        logger_main.info("No credentials for API")
        apiThread = threading.Thread(target=APIFunction, daemon=True, kwargs={'airspace':airspace})
    apiThread.start()
    
    serThread = threading.Thread(target=SerialFunction, daemon=True, args=(airspace, ))
    serThread.start()

    print("Starting display routine")
    while True:
        time.sleep(5)
        with airspace._lock:
            for craft in airspace.crafts:
                print(craft)
        
    print('Bye!')
    ardi.close()

