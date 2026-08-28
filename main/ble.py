#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK
#
# BSD 3-Clause License
# Copyright (c) 2022-2024, Thomas Breitbach
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from bleak import BleakClient, BleakScanner
from globals import rlog
from pathlib import Path
import re
import time
import traceback
import json
import arguments


SERVICE = "ffe0"
CHARACTERISTIC = "ffe1"
BLE_BASE_UUID = "0000{0}-0000-1000-8000-00805f9b34fb"
service_uuid = BLE_BASE_UUID.format(SERVICE.lower())
characteristic_uuid = BLE_BASE_UUID.format(CHARACTERISTIC.lower())
OGN_DDB_FILENAME = str(Path(arguments.FULL_CONFIG_DIR).joinpath("ddb.json"))

global_situation = None    # global situation dictionary to hold the latest situation data
traffic_func = None         # global function to handle new traffic messages
situation_func = None       # global function to handle new situation messages
ble_address = None             # global BLE address to connect to
ogn_tail_number_cache = {}     # global cache for OGN tail numbers consisting of ognid -> tail number mappings
ogn_device_db_loaded = False


def is_valid_ble_address(address: str) -> bool:
    mac_regex = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")
    return bool(mac_regex.match(address))


def lookup_ogn_tail_number(ognid):
    # return the tail number for the given OGN ID from the cache, or load the OGN device database if not already loaded
    # function like in stratux ogn.go
    global ogn_device_db_loaded
    if not ogn_device_db_loaded:
        ogn_device_db_loaded = True
        rlog.debug(f"Ble: Parsing OGN device db {OGN_DDB_FILENAME}")
        try:
            with Path(OGN_DDB_FILENAME).open("r", encoding="utf-8") as db_file:
                data = json.load(db_file)
        except (OSError, json.JSONDecodeError) as e:
            rlog.debug(f"Ble: Failed to parse OGN device db {OGN_DDB_FILENAME}: {e}")
            return ognid

        devices = data.get("devices", [])
        if not isinstance(devices, list):
            rlog.debug(f"Ble: Failed to parse OGN device db {OGN_DDB_FILENAME}: invalid devices structure")
            return ognid
        for device in devices:
            if not isinstance(device, dict):
                continue
            device_id = device.get("device_id")
            registration = device.get("registration")
            if isinstance(device_id, str) and isinstance(registration, str):
                ogn_tail_number_cache[device_id] = registration
        rlog.debug(f"Ble: {OGN_DDB_FILENAME} loaded with {len(ogn_tail_number_cache)} entries")
        print(f"ogn_tail_number_cache: {ogn_tail_number_cache}")
    return ogn_tail_number_cache.get(ognid, "")


# declare an empty global situation message to hold the data
situation_msg = {
    'GPSLatitude': 0,
    'GPSLongitude': 0,
    'BaroPressureAltitude': 0,
    'GPSTrueCourse': 0,
    'GPSGroundSpeed': 0,     # in knots
    'BaroVerticalSpeed': 0,
    'GPSHorizontalAccuracy': 0,
    'GPSVerticalAccuracy': 0,
    'GPSFixQuality': 0,
    'GPSLastFixLocalTime': time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    'GPSLastGPSTimeStratuxTime': time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    'GPSTime': time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    'GPSAltitudeMSL': 0,   # in feet
    'BaroSourceType': 1,
    'AHRSPitch': 0,
    'AHRSRoll': 0,
    'AHRSGyroHeading': 0,
    'AHRSSlipSkid': 0,
    'AHRSStatus': 0,
    'AHRSGLoad': 1.0,
    'AHRSGLoadMax': 1.0,
    'AHRSGLoadMin': 1.0
}


traffic_msg = None  # Will be set by parse_traffic_msg() or parse_PFLAA()



def check_nmea_checksum(data, provided_checksum):
    # Calculate XOR checksum of all characters between '$' and '*'
    calculated_checksum = 0
    for char in data:
        calculated_checksum ^= ord(char)
    calculated_hex = f"{calculated_checksum:02X}"
    # Compare with the provided checksum (case-insensitive)
    return calculated_hex == provided_checksum.upper()

def parse_traffic_msg(icao_addr, latitude, longitude, altitude, track, speed, vspeed, tail):
     """Create a traffic_msg dictionary with parsed aircraft data"""
     return {
         'Icao_addr': icao_addr,
         'Lat': latitude,
         'Lng': longitude,
         'Alt': altitude,
         'Track': track,
         'Speed': speed,
         'Vvel': vspeed,
         'Speed_valid': True,
         'Position_valid': True,
         'Age': 0,
         'AgeLastAlt': 0,
         'Last_source': 1,  # 1090ES
         'Tail': tail,
         'DistanceEstimated': 0
     }

def coordinates_from_relative(rel_north, rel_east, lat_own, lon_own):
     # Convert relative North/East distances in meters to absolute lat/lon coordinates
     # Earth radius in meters
     EARTH_RADIUS = 6371000
     # Convert to radians
     lat_rad = lat_own * (3.14159265359 / 180)
     dlat = (rel_north / EARTH_RADIUS) * (180 / 3.14159265359)
     # Calculate change in longitude (accounting for latitude)
     if lat_rad == 0:
         dlon = 0
     else:
        dlon = (rel_east / (EARTH_RADIUS * abs(3.14159265359 * lat_rad / 180))) * (180 / 3.14159265359)
     return lat_own + dlat, lon_own + dlon


def parse_PFLAA(fields):
    # Format: $PFLAA,<AlarmLevel>,<RelNorth_m>,<RelEast_m>,<RelVert_m>,<IDType>,<ID>,<Track>,<TurnRate>,<GS_ms>,<ClimbRate_ms>,<AcftType>*hh
    # Example: PFLAA,0,1234,-567,120,2,3D02A4,115,,25,1.5,3
    # Fields description:
    #   [1] AlarmLevel  : 0=no alarm, 1=low, 2=important, 3=urgent
    #   [2] RelativeNorth: distance north of own position in meters (negative = south)
    #   [3] RelativeEast : distance east  of own position in meters (negative = west)
    #   [4] RelativeVert : altitude difference in meters             (negative = below)
    #   [5] IDType       : 1=Random, 2=ICAO, 3=FLARM
    #   [6] ID           : hex aircraft address (ICAO or FLARM ID)
    #   [7] Track        : true track in degrees 0-359 (may be empty)
    #   [8] TurnRate     : degrees/s (may be empty, not used)
    #   [9] GroundSpeed  : m/s (may be empty)
    #  [10] ClimbRate    : m/s, positive = climbing (may be empty)
    #  [11] AcftType     : aircraft type code (not used)
    global situation_msg
    if len(fields) < 11:
        rlog.debug(f"NMEA: Incomplete PFLAA sentence: {fields}")
        return None
    if global_situation is None:
        rlog.debug(f"NMEA: Ignoring PFLAA without own situation: {fields}")
        return None
    try:
        own_situation = global_situation if isinstance(global_situation, dict) else {}
        rel_north = float(fields[2])                          # meters, north positive
        rel_east  = float(fields[3])                          # meters, east  positive
        rel_vertical = float(fields[4])                       # meters, above positive
        icao_addr_str = fields[6]
        icao_addr = int(icao_addr_str, 16) if icao_addr_str else 0
        track       = float(fields[7]) if fields[7] else 0.0
        speed_mps   = float(fields[9])  if fields[9]  else 0.0
        climb_mps   = float(fields[10]) if fields[10] else 0.0
        speed_knots  = float(speed_mps  * 1.94384)   # m/s  → knots
        vspeed_ftmin = float(climb_mps  * 196.85)    # m/s  → ft/min

        # Convert relative offsets to absolute WGS-84 coordinates
        own_lat = float(own_situation['latitude'])
        own_lon = float(own_situation['longitude'])
        lat, lon = coordinates_from_relative(rel_north, rel_east, own_lat, own_lon)
        lat = float(lat)
        lon = float(lon)

        # Absolute altitude in feet (own baro altitude + relative vertical converted to feet)
        own_alt_ft = float(own_situation['own_altitude'])
        altitude_ft  = own_alt_ft + (rel_vertical * 3.28084)

        tail = lookup_ogn_tail_number(icao_addr_str) or icao_addr_str
        msg = parse_traffic_msg(icao_addr= icao_addr, latitude=lat, longitude=lon, altitude=altitude_ft,
            track=track, speed=speed_knots, vspeed=vspeed_ftmin,tail=tail)
        msg['Last_source'] = 4   # SOURCE_FLARM (as defined in radar.py)
        rlog.debug(f"NMEA: PFLAA parsed - ID: {icao_addr_str}, Lat: {lat:.5f}, Lon: {lon:.5f}, "
                 f"Alt: {altitude_ft:.0f}ft, Track: {track}°, Speed: {speed_knots:.1f}kt, "
                 f"Vspeed: {vspeed_ftmin:.0f}fpm")
        return msg

    except (ValueError, KeyError) as e:
        rlog.debug(f"NMEA: Error parsing PFLAA fields: {fields} - {e}")
        traceback.print_exc()
        return None


def parse_GNGLL(fields):
    # Parse GNGLL NMEA sentence and update situation_msg
    # Format: $GNGLL,lat,N/S,lon,E/W,hhmmss.ss,A/V*hh
    global situation_msg
    if len(fields) < 7:
        rlog.debug(f"NMEA: Incomplete GNGLL sentence: {fields}")
        return False

    try:
        # Parse latitude (DDMM.MMMMM format)
        if fields[1] and fields[2]:
            lat = float(fields[1])
            lat_degrees = int(lat / 100)
            lat_minutes = lat - (lat_degrees * 100)
            latitude = lat_degrees + (lat_minutes / 60)
            # Apply N/S direction
            if fields[2].upper() == 'S':
                latitude = -latitude
            situation_msg['GPSLatitude'] = latitude
        # Parse longitude (DDDMM.MMMMM format)
        if fields[3] and fields[4]:
            lon = float(fields[3])
            lon_degrees = int(lon / 100)
            lon_minutes = lon - (lon_degrees * 100)
            longitude = lon_degrees + (lon_minutes / 60)
            # Apply E/W direction
            if fields[4].upper() == 'W':
                longitude = -longitude
            situation_msg['GPSLongitude'] = longitude
        # Parse UTC time (hhmmss.ss format)
        if fields[5]:
            situation_msg['GPSTime'] = fields[5]
        # Parse fix status (A=valid, V=invalid)
        if fields[6]:
            is_valid = fields[6].upper() == 'A'
            situation_msg['GPSFixQuality'] = 1 if is_valid else 0
        rlog.debug(f"NMEA: GNGLL parsed - Lat: {situation_msg['GPSLatitude']}, Lon: {situation_msg['GPSLongitude']}, Status: {situation_msg['GPSFixQuality']}")
        return True
    except ValueError as e:
        rlog.debug(f"NMEA: Error parsing GNGLL fields: {fields} - {e}")
        return False


def parse_GNGGA(fields):
    # Parse GNGGA NMEA sentence and update situation_msg
    # Format: $GNGGA,hhmmss.ss,lat,N/S,lon,E/W,fix_quality,num_satellites,hdop,altitude,M,geoid_sep,M,dgps_age,dgps_station_id*hh
    global situation_msg
    if len(fields) < 15:
        rlog.debug(f"NMEA: Incomplete GNGGA sentence: {fields}")
        return False
    try:
        # Parse fix quality (0=invalid, 1=GPS fix, 2=DGPS fix)
        if fields[6]:
            situation_msg['GPSFixQuality'] = int(fields[6])
        # Parse number of satellites
        if fields[7]:
            situation_msg['NumSatellites'] = int(fields[7])
        # Parse horizontal dilution of precision (HDOP)
        if fields[8]:
            situation_msg['GPSHorizontalAccuracy'] = float(fields[8])
        # Parse altitude above mean sea level (in meters)
        if fields[9]:
            situation_msg['GPSAltitudeMSL'] = float(fields[9]) * 3.28084  # Convert meters to feet
        rlog.debug(f"NMEA: GNGGA parsed - Fix Quality: {situation_msg['GPSFixQuality']}, Num Satellites: {situation_msg['NumSatellites']}, Altitude MSL/ft: {situation_msg['GPSAltitudeMSL']}")
        return True
    except ValueError as e:
        rlog.debug(f"NMEA: Error parsing GNGGA fields: {fields} - {e}")
        traceback.print_exc()
        return False


def _parse_nmea_coordinate(value, hemisphere, degree_digits):
    if not value or not hemisphere:
        raise ValueError("Missing coordinate value or hemisphere")
    degrees = int(value[:degree_digits])
    minutes = float(value[degree_digits:])
    coordinate = degrees + (minutes / 60.0)
    if hemisphere.upper() in ('S', 'W'):
        coordinate = -coordinate
    return coordinate


def _parse_rmc(fields, sentence_type):
    # Common parser for GPRMC / GNRMC / GNMRC sentences
    # Format: $--RMC,hhmmss.ss,A,lat,N,lon,E,speed,track,date,magvar,E/W*hh
    global situation_msg
    if len(fields) < 12:
        rlog.debug(f"NMEA: Incomplete {sentence_type} sentence: {fields}")
        return False
    try:
        if fields[1]:
            situation_msg['GPSTime'] = fields[1]
        if fields[2]:
            situation_msg['GPSFixQuality'] = 1 if fields[2].upper() == 'A' else 0
        if fields[3] and fields[4]:
            situation_msg['GPSLatitude'] = _parse_nmea_coordinate(fields[3], fields[4], 2)
        if fields[5] and fields[6]:
            situation_msg['GPSLongitude'] = _parse_nmea_coordinate(fields[5], fields[6], 3)
        if fields[7]:
            situation_msg['GPSGroundSpeed'] = float(fields[7])
        if fields[8]:
            situation_msg['GPSTrueCourse'] = float(fields[8])
        rlog.debug(
            f"NMEA: {sentence_type} parsed - Lat: {situation_msg['GPSLatitude']}, "
            f"Lon: {situation_msg['GPSLongitude']}, Speed: {situation_msg['GPSGroundSpeed']}, "
            f"Course: {situation_msg['GPSTrueCourse']}"
        )
        return True
    except (ValueError, IndexError) as e:
        rlog.debug(f"NMEA: Error parsing {sentence_type} fields: {fields} - {e}")
        traceback.print_exc()
        return False


def parse_GPRMC(fields):
    # Parse GPRMC NMEA sentence and update situation_msg
    # Format: $GPRMC,hhmmss.ss,A,lat,N,lon,E,speed,track,date,magvar,E/W*hh
    return _parse_rmc(fields, "GPRMC")

def parse_GNGSA(fields):
    # Parse GNGSA NMEA sentence and update situation_msg
    # Format: $GNGSA,<Mode>,<FixType>,<PRN1>,...,<PRN12>,<PDOP>,<HDOP>,<VDOP>*hh
    global situation_msg
    if len(fields) < 17:
        rlog.debug(f"NMEA: Incomplete GNGSA sentence: {fields}")
        return False
    try:
        # Parse fix type (1=No fix, 2=2D fix, 3=3D fix)
        if fields[2]:
            situation_msg['GPSFixQuality'] = int(fields[2])
        # Parse HDOP, VDOP values
        if fields[16]:
            situation_msg['GPSHorizontalAccuracy'] = float(fields[16])
        if len(fields) > 17 and fields[17]:
            situation_msg['GPSVerticalAccuracy'] = float(fields[17])
        rlog.debug(f"NMEA: GNGSA parsed - Fix Quality: {situation_msg['GPSFixQuality']}, PDOP: {situation_msg.get('PDOP', 'N/A')}, HDOP: {situation_msg.get('GPSHorizontalAccuracy', 'N/A')}, VDOP: {situation_msg.get('GPSVerticalAccuracy', 'N/A')}")
        return True
    except ValueError as e:
        rlog.debug(f"NMEA: Error parsing GNGSA fields: {fields} - {e}")
        traceback.print_exc()
        return False

def parse_GNRMC(fields):
    # Parse GNRMC NMEA sentence and update situation_msg
    # Format: $GNRMC,hhmmss.ss,A,lat,N,lon,E,speed,track,date,magvar,E/W*hh
    return _parse_rmc(fields, "GNRMC")


def parse_POGNB(fields):
    # Parse POGNB NMEA sentence and update situation_msg
    # Format: $POGNB,<BaroAltitude>,<BaroVerticalSpeed>,<AHRSPitch>,<AHRSRoll>,<AHRSGyroHeading>,<AHRSSlipSkid>,<AHRSStatus>,<AHRSGLoad>,<AHRSGLoadMax>,<AHRSGLoadMin>*hh
    global situation_msg
    if len(fields) < 11:
        rlog.debug(f"NMEA: Incomplete POGNB sentence: {fields}")
        return False
    try:
        if fields[1]:
            situation_msg['BaroPressureAltitude'] = float(fields[1])
        if fields[2]:
            situation_msg['BaroVerticalSpeed'] = float(fields[2])
        if fields[3]:
            situation_msg['AHRSPitch'] = float(fields[3])
        if fields[4]:
            situation_msg['AHRSRoll'] = float(fields[4])
        if fields[5]:
            situation_msg['AHRSGyroHeading'] = float(fields[5])
        if fields[6]:
            situation_msg['AHRSSlipSkid'] = float(fields[6])
        if fields[7]:
            situation_msg['AHRSStatus'] = int(fields[7])
        if fields[8]:
            situation_msg['AHRSGLoad'] = float(fields[8])
        if fields[9]:
            situation_msg['AHRSGLoadMax'] = float(fields[9])
        if fields[10]:
            situation_msg['AHRSGLoadMin'] = float(fields[10])
        rlog.debug(f"NMEA: POGNB parsed - Baro Altitude: {situation_msg['BaroPressureAltitude']}, Vertical Speed: {situation_msg['BaroVerticalSpeed']}, Pitch: {situation_msg['AHRSPitch']}, Roll: {situation_msg['AHRSRoll']}, Gyro Heading: {situation_msg['AHRSGyroHeading']}")
        return True
    except ValueError as e:
        rlog.debug(f"NMEA: Error parsing POGNB fields: {fields} - {e}")
        traceback.print_exc()
        return False

def parse_GNMRC(fields):
    # Some BLE/NMEA sources appear to emit the non-standard talker/type GNMRC.
    # Parse it like a regular RMC sentence for compatibility.
    return _parse_rmc(fields, "GNMRC")

def parse_GNVTG(fields):
    # Parse GNVTG NMEA sentence and update situation_msg
    # Format: $GNVTG,<TrackTrue>,T,<TrackMagnetic>,M,<SpeedKnots>,N,<SpeedKmh>,K*hh
    global situation_msg
    if len(fields) < 9:
        rlog.debug(f"NMEA: Incomplete GNVTG sentence: {fields}")
        return False
    try:
        # Parse track over ground in degrees (true)
        if fields[1]:
            situation_msg['GPSTrueCourse'] = float(fields[1])
        # Parse speed over ground in knots
        if fields[5]:
            speed_knots = float(fields[5])
            situation_msg['GPSGroundSpeed'] = speed_knots
        rlog.debug(f"NMEA: GNVTG parsed - Course: {situation_msg['GPSTrueCourse']}, Speed: {situation_msg['GPSGroundSpeed']}")
        return True
    except ValueError as e:
        rlog.debug(f"NMEA: Error parsing GNVTG fields: {fields} - {e}")
        traceback.print_exc()
        return False


def _emit_situation_update(callback):
    if callback is not None:
        callback(json.dumps(situation_msg))


def _emit_traffic_update(callback, message):
    if callback is not None:
        callback(json.dumps(message))


def handle_nmea_data(nmea_sentence):
    traffic_callback = traffic_func
    situation_callback = situation_func
    # Verify checksum before parsing
    if "*" not in nmea_sentence:
        rlog.debug(f"NMEA: Invalid NMEA sentence: Missing checksum")
        return
    data, checksum = nmea_sentence.strip().split("*")
    # Remove leading '$' if present
    if data.startswith("$"):
        data = data[1:]
    if not check_nmea_checksum(data, checksum):
        rlog.debug(f"NMEA: Invalid checksum for sentence: {nmea_sentence}")
        return
    fields = data.split(",")  # Split the fields
    if not fields:
        rlog.debug(f"NMEA: Empty fields in sentence: {nmea_sentence}")
        return
    if fields[0] == "GNGLL":
        if parse_GNGLL(fields):
            _emit_situation_update(situation_callback)
    elif fields[0] == "GPRMC":
        if parse_GPRMC(fields):
            _emit_situation_update(situation_callback)
    elif fields[0] == "PFLAU":
        # ignore PFLAU for now, as it is not used in the current implementation
        pass
    elif fields[0] == "PFLAA":
        traffic_msg_parsed = parse_PFLAA(fields)
        if traffic_msg_parsed:
            _emit_traffic_update(traffic_callback, traffic_msg_parsed)
    elif fields[0] == "GNGGA":
        if parse_GNGGA(fields):
            _emit_situation_update(situation_callback)
    elif fields[0] == "GNGSA":
        if parse_GNGSA(fields):
            _emit_situation_update(situation_callback)
    elif fields[0] == "GNRMC":
        if parse_GNRMC(fields):
            _emit_situation_update(situation_callback)
    elif fields[0] == "GNMRC":
        if parse_GNMRC(fields):
            _emit_situation_update(situation_callback)
    elif fields[0] == "GNVTG":
        if parse_GNVTG(fields):
            _emit_situation_update(situation_callback)
    elif fields[0] == "POGNB":
        if parse_POGNB(fields):
            _emit_situation_update(situation_callback)
    else:
        rlog.debug(f"NMEA: Unhandled NMEA sentence type: {fields[0]}")


async def listen_to_ble():
    address = ble_address
    if address is None:
        rlog.debug("Ble: No BLE address configured")
        return
    valid_address = str(address)
    if not is_valid_ble_address(valid_address):
        rlog.debug(f"Ble: Invalid BLE address format: {address}")
        return
    device_address = valid_address
    device_uuid = characteristic_uuid
    device= {'name': f"Unknown ({device_address})", 'address': device_address, 'uuid': device_uuid}
    try:
        async with BleakClient(device_address) as client:
            if client.is_connected:
                rlog.debug(f"Ble: Connected to {device['address']}")
                while True:
                    data = await client.read_gatt_char(device_uuid)
                    # convert type of data to a string
                    data = data.decode('utf-8').strip()
                    rlog.debug(f"Ble: Received data: {data}")
                    # accept also concatenated several NMEA sentences in one read,
                    for nmea_sentence in data.split("\r\n"):
                        if nmea_sentence:
                            handle_nmea_data(nmea_sentence)
            else:
                rlog.debug(f"Ble: Failed to connect to {device['address']}")
    except Exception as e:
        rlog.debug(f"Ble: Exception while listening to BLE device {ble_address}: {e}")
        traceback.print_exc()


async def search_ble():
    # search for ble devices, returns list of dictionaries with name and address of devices that offer the service FFE0
    found_devices = []
    try:
        scanner = BleakScanner()
        devices = await scanner.discover(timeout=10)
    except Exception as e:
        rlog.debug(f"Ble: Exception performing BLE-Scan: {e}")
        return []
    # accept only devices with device id FFE0
    rlog.debug(f"Identified devices: {devices}")
    for device in devices:
        uuids = device.details.get("props").get("UUIDs")
        rlog.debug(f"Ble: Found device {device.name} ({device.address}) with UUIDs: {uuids}")
        for uuid in uuids:
            if  uuid == service_uuid:
                device_info = {
                    'name': device.name if device.name else f"Unknown ({device.address})",
                    'address': device.address,
                    'uuid': characteristic_uuid
                }
                found_devices.append(device_info)
        rlog.debug(f"Ble: Following BLE devices with service FFE0 found: {found_devices}")
    return found_devices


def init(new_ble_address, new_traffic_func, new_situation_func, situation):
    global global_situation
    global traffic_func
    global situation_func
    global ble_address

    global_situation = situation
    traffic_func = new_traffic_func
    situation_func = new_situation_func
    ble_address = new_ble_address
    rlog.debug("BLE initialized with address: {0}".format(ble_address))


