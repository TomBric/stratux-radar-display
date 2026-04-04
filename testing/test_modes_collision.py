#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# testmodule to test collision detection for mode s targets
# usage:   python3 test_modes_collision.py -f <test_file>

import sys
import os
import time
import argparse

# Add the main directory to the path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'main'))
# Import the actual modules
from globals import rlog, AIRCRAFT_DEBUG

# Set logging to AIRCRAFT_DEBUG mode
rlog.setLevel(AIRCRAFT_DEBUG)
# Import the actual collisiondetect module
import collisiondetect

rlog.setLevel(AIRCRAFT_DEBUG)
def parse_test_file_line(line):
    # Remove commas and split by whitespace or commas
    line = line.replace(',', ' ')
    parts = line.strip().split()
    return parts

def file_based_test(filename):
    if not os.path.exists(filename):
        print(f"Error: Test file '{filename}' not found.")
        return
    
    print(f"Reading Mode-S test cases from: {filename}")
    print("=" * 60)
    
    test_cases = []
    current_case = []
    line_number = 0
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line_number += 1
                line = line.strip()
                if not line or line.startswith('#'): 
                    continue
                current_case.append((line_number, line))
                if len(current_case) == 3: 
                    test_cases.append(current_case.copy())
                    current_case.clear()
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
    
    # Situation is constant for Mode-S relative tests in this script
    situation = {
        'own_altitude': 5000,
        'vertical_speed': 0
    }

    for i, test_case in enumerate(test_cases, 1):
        print(f"Test Case {i}:")
        print("-" * 40)
        
        try:
            # Line 1: initial_timeout, initial_alt, initial_dist_nm
            traffic_init = parse_test_file_line(test_case[0][1])
            init_timeout = float(traffic_init[0])
            init_alt = float(traffic_init[1])
            init_dist_nm = float(traffic_init[2])
            
            # Line 2: updates (timeout, alt, dist_nm)
            updates = []
            update_parts = parse_test_file_line(test_case[1][1])
            for j in range(0, len(update_parts), 3):
                updates.append({
                    'timeout': float(update_parts[j]),
                    'alt': float(update_parts[j+1]),
                    'dist': float(update_parts[j+2])
                })
            
            # Line 3: Expected result
            expected_result = test_case[2][1].strip()

            # Setup Mock Aircraft
            now = time.time()
            ac = {
                'Icao_addr': 0x123456,
                'DistanceEstimated': init_dist_nm,
                'alt': init_alt,
                'hdiff': round((init_alt - situation['own_altitude']) / 100),
                'last_alt_timestamp': now - init_timeout
            }

            print(f"Initial: Timeout={init_timeout}s, Alt={init_alt}ft, Dist={init_dist_nm}nm")
            
            # Initial classification to start filters
            actual_result = collisiondetect.calc_modes_tcas_state(ac, situation)
            print(f"  Initial State: {actual_result}")

            # Simulate updates with real sleeps
            for up in updates:
                time.sleep(up['timeout'])
                now = time.time()
                
                ac['gps_distance'] = up['dist']
                ac['alt'] = up['alt']
                ac['hdiff'] = round((up['alt'] - situation['own_altitude']) / 100)
                ac['last_alt_timestamp'] = now
                
                # We call the classification which triggers the filter update
                actual_result = collisiondetect.calc_modes_tcas_state(ac, situation)
                print(f"  Update: timeout={up['timeout']}s, alt={up['alt']}ft, dist={up['dist']}nm -> {actual_result}")

            print(f"Expected: {expected_result}")
            print(f"Actual:   {actual_result}")

            if actual_result == expected_result:
                print("✓ PASS")
                passed += 1
            else:
                print("✗ FAIL")
                failed += 1
        except Exception as e:
            print(f"✗ ERROR: {e}")
            failed += 1
        print()

    print("=" * 60)
    print(f"Test Summary: {passed} passed, {failed} failed out of {len(test_cases)} total")
    print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description='Mode-S TCAS State Test')
    parser.add_argument('-f', '--file', help='Test cases file', required=True)
    args = parser.parse_args()
    file_based_test(args.file)

if __name__ == "__main__":
    main()
