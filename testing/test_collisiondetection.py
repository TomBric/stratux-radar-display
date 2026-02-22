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
import argparse

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


def parse_test_file_line(line):
    """Parse a line with 6 float values and return them as a list"""
    # Remove commas and split by whitespace or commas
    line = line.replace(',', ' ')
    parts = line.strip().split()
    if len(parts) != 6:
        raise ValueError(f"Line must contain exactly 6 values, got {len(parts)}: {line.strip()}")
    return [float(part) for part in parts]

def file_based_test(filename):
    """Run test cases from a file"""
    global situation
    
    if not os.path.exists(filename):
        print(f"Error: Test file '{filename}' not found.")
        return
    
    print(f"Reading test cases from: {filename}")
    print("=" * 60)
    
    test_cases = []
    current_case = []
    line_number = 0
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line_number += 1
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                # Add non-empty, non-comment lines to current case
                current_case.append((line_number, line))
                # When we have 3 lines, we have a complete test case
                if len(current_case) == 3:
                    test_cases.append(current_case.copy())
                    current_case.clear()
            # Handle case where file doesn't end with complete test case
            if current_case:
                print(f"Warning: Incomplete test case at end of file (lines {[case[0] for case in current_case]})")
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    if not test_cases:
        print("No valid test cases found in file.")
        return
    print(f"Found {len(test_cases)} test case(s)")
    print()
    
    passed = 0
    failed = 0
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test Case {i}:")
        print("-" * 40)
        
        try:
            # Parse traffic data (line 1)
            traffic_line = test_case[0][1]
            traffic_data = parse_test_file_line(traffic_line)
            traffic_lat, traffic_lng, traffic_alt, traffic_track, traffic_speed_kts, traffic_vspeed_ftmin = traffic_data
            
            # Parse own data (line 2)
            own_line = test_case[1][1]
            own_data = parse_test_file_line(own_line)
            own_lat, own_lng, own_alt, own_course, own_speed_kts, own_vspeed_ftmin = own_data
            
            # Parse expected result (line 3)
            expected_line = test_case[2][1].strip()
            expected_result = expected_line

            # Set up situation
            situation = {
                'gps_active': True,
                'gps_speed': own_speed_kts,  # horizontal speed in ft/min
                'own_altitude': own_alt,
                'latitude': own_lat,
                'longitude': own_lng,
                'course': own_course,
                'vertical_speed': own_vspeed_ftmin  # vertical speed in kts
            }

            # Set up traffic
            traffic = {
                'Alt': traffic_alt,
                'Lat': traffic_lat,
                'Lng': traffic_lng,
                'Track': traffic_track,
                'Speed': traffic_speed_kts,  # horizontal speed in ft/min
                'VSpeed': traffic_vspeed_ftmin  # vertical speed in kts
            }

            print(f"Traffic: Lat={traffic_lat:.6f}, Lng={traffic_lng:.6f}, Alt={traffic_alt:.0f}ft, Track={traffic_track:.0f}°, HSpeed={traffic_speed_kts:.0f}kts, VSpeed={traffic_vspeed_ftmin:.0f}ft/min")
            print(f"Own:    Lat={own_lat:.6f}, Lng={own_lng:.6f}, Alt={own_alt:.0f}ft, Course={own_course:.0f}°, HSpeed={own_speed_kts:.0f}kts, VSpeed={own_vspeed_ftmin:.0f}ft/min")
            print(f"Expected: {expected_result}")

            # Calculate distance and bearing
            distance, bearing = calc_gps_distance(traffic_lat, traffic_lng)
            print(f"Info: distance of aircraft = {distance:.1f} nm")
        except Exception as e:
            print(f"✗ ERROR: {e}")
            failed += 1
            continue

        # Execute TCAS calculation
        actual_result = calc_tcas_state(traffic, situation)

        print(f"Actual:   {actual_result}")

        # Check if result matches expectation
        if actual_result == expected_result:
            print("✓ PASS")
            passed += 1
        else:
            print("✗ FAIL")
            failed += 1


        print()
    
    print("=" * 60)
    print(f"Test Summary: {passed} passed, {failed} failed out of {len(test_cases)} total")
    print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description='TCAS State Calculator Test')
    parser.add_argument('-f', '--file', help='File containing test cases (format: 3 lines per test case)', required=True)
    
    args = parser.parse_args()
    
    # Display TCAS thresholds used in collision detection
    print("=" * 60)
    print("TCAS State Calculator Test")
    print("=" * 60)
    print()
    print("=== Thresholds ===")
    print(f"COLLISION_THRESHOLD: {collisiondetection.COLLISION_THRESHOLD} seconds")
    print(f"COLLISION_DIST_THRESHOLD: {collisiondetection.COLLISION_DIST_THRESHOLD} nm")
    print(f"COLLISION_ALT_THRESHOLD, {collisiondetection.COLLISION_ALT_THRESHOLD} ft")
    print(f"TA_THRESHOLD: {collisiondetection.TA_THRESHOLD} seconds")
    print(f"TA_DIST_THRESHOLD: {collisiondetection.TA_DIST_THRESHOLD} NM")
    print(f"TA_ALT_THRESHOLD: {collisiondetection.TA_ALT_THRESHOLD} feet")
    print(f"RA_THRESHOLD: {collisiondetection.RA_THRESHOLD} seconds")
    print(f"RA_DIST_THRESHOLD: {collisiondetection.RA_DIST_THRESHOLD} NM")
    print(f"RA_ALT_THRESHOLD: {collisiondetection.RA_ALT_THRESHOLD} feet")
    print()
    
    # File-based testing (now the only mode)
    file_based_test(args.file)

if __name__ == "__main__":
    main()

