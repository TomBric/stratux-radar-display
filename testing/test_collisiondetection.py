#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK
#
# BSD 3-Clause License
# Copyright (c) 2026, Thomas Breitbach
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
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE

import sys
import os
import math

# Add the main directory to the path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'main'))
# Import the actual modules
from globals import rlog, AIRCRAFT_DEBUG

# Set logging to AIRCRAFT_DEBUG mode
rlog.setLevel(AIRCRAFT_DEBUG)
# Import the actual collisiondetection module
import collisiondetection
calc_tcas_state = collisiondetection.calc_tcas_state

situation = {}


# from radar.py
def radians_rel(angle):
    if angle > 180:
        angle = angle - 360
    if angle <= -180:
        angle = angle + 360
    return angle * math.pi / 180

# calc_gps_distance from radar.py
def calc_gps_distance(lat, lng):
    radius_earth = 6371008.8
    avglat = radians_rel((situation['latitude'] + lat) / 2)
    distlat = (radians_rel(lat - situation['latitude']) * radius_earth) / 1852
    distlng = ((radians_rel(lng - situation['longitude']) * radius_earth) / 1852) * abs(math.cos(avglat))
    distradius = math.sqrt((distlat * distlat) + (distlng * distlng))
    if distlat < 0:
        angle = math.degrees(math.pi - math.atan(distlng / (-distlat)))
    elif distlat > 0:
        angle = math.degrees(-math.atan(distlng / (-distlat)))
    else:
        angle = 0
    return distradius, angle


def get_float_input(prompt, default=None):
    """Helper function to get float input with validation"""
    while True:
        try:
            if default is not None:
                value = input(f"{prompt} (default: {default}): ").strip()
                if not value:
                    return float(default)
            else:
                value = input(f"{prompt}: ").strip()
            return float(value)
        except ValueError:
            print("Invalid input. Please enter a valid number.")

def get_int_input(prompt, default=None):
    """Helper function to get integer input with validation"""
    while True:
        try:
            if default is not None:
                value = input(f"{prompt} (default: {default}): ").strip()
                if not value:
                    return int(default)
            else:
                value = input(f"{prompt}: ").strip()
            return int(value)
        except ValueError:
            print("Invalid input. Please enter a valid integer.")

def get_yes_no_input(prompt, default=True):
    """Helper function to get yes/no input"""
    while True:
        if default:
            value = input(f"{prompt} (Y/n): ").strip().lower()
        else:
            value = input(f"{prompt} (y/N): ").strip().lower()

        if not value:
            return default
        if value in ['y', 'yes', 'j', 'ja']:
            return True
        elif value in ['n', 'no', 'nein']:
            return False
        else:
            print("Invalid input. Please enter 'y' or 'n'.")

def interactive_test():
    global situation

    print("=" * 60)
    print("Interactive TCAS State Calculator Test")
    print("=" * 60)
    print()
    
    # Get situation data
    print("=== Own Aircraft Situation ===")
    gps_active = get_yes_no_input("GPS active", True)
    gps_speed = get_float_input("GPS speed (knots)", 100.0)
    own_altitude = get_float_input("Own altitude (feet)", 5000.0)
    own_lat = get_float_input("Own latitude (decimal degrees)", 48.0)
    own_lng = get_float_input("Own longitude (decimal degrees)", 11.0)
    course = get_float_input("Course (degrees)", 0.0)
    vertical_speed = get_float_input("Vertical speed (ft/min, positive=climbing)", 0.0)
    
    situation = {
        'gps_active': gps_active,
        'gps_speed': gps_speed,
        'own_altitude': own_altitude,
        'latitude': own_lat,
        'longitude': own_lng,
        'course': course,
        'vertical_speed': vertical_speed
    }
    
    print()
    print("=== Traffic Aircraft Data ===")
    traffic_alt = get_float_input("Traffic altitude (feet)", 4500.0)
    traffic_lat = get_float_input("Traffic latitude (decimal degrees)", 48.0)
    traffic_lng = get_float_input("Traffic longitude (decimal degrees)", 11.0)
    traffic_track = get_float_input("Traffic track (degrees)", 180.0)
    traffic_speed = get_float_input("Traffic speed (knots)", 100.0)
    traffic_vspeed = get_float_input("Traffic vertical speed (ft/min)", 0.0)
    
    traffic = {
        'Alt': traffic_alt,
        'Lat': traffic_lat,
        'Lng': traffic_lng,
        'Track': traffic_track,
        'Speed': traffic_speed,
        'VSpeed': traffic_vspeed
    }
    
    print()
    print("=== Calculating Relative Position ===")
    print(f"Using calc_gps_distance to calculate distance and bearing from own position ({own_lat:.4f}, {own_lng:.4f}) to traffic position ({traffic_lat:.4f}, {traffic_lng:.4f})")
    
    # Calculate distance and bearing using the actual function from radar.py
    distance, bearing = calc_gps_distance(traffic_lat, traffic_lng)
    
    print(f"Calculated distance: {distance:.3f} NM")
    print(f"Calculated bearing: {bearing:.1f}°")
    
    print()
    print("=" * 60)
    print("Executing TCAS State Calculation...")
    print("=" * 60)
    print()
    
    # Execute the function
    result = calc_tcas_state(traffic, distance, bearing, situation)
    
    print()
    print("=" * 60)
    print(f"Result: {result}")
    print("=" * 60)

def main():
    while True:
        interactive_test()

if __name__ == "__main__":
    main()

