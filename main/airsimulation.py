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

import asyncio
import json
import time
from pathlib import Path
from globals import rlog, AIRCRAFT_DEBUG, SITUATION_DEBUG
# Import radar functions for callbacks
import radar

# Global variables for simulation state
simulation_file = None
simulation_lines = []
current_line_index = 0
last_event_time = 0.0

async def sim_handler(aircraft_sim_file):
    global simulation_file, simulation_lines, current_line_index, last_event_time
    
    if aircraft_sim_file is None:
        rlog.debug("Sim-Handler: No file provided. Stopping.")
        return
    
    # Initialize simulation file
    if simulation_file is None:
        try:
            file_path = Path(aircraft_sim_file)
            if not file_path.exists():
                rlog.debug(f"Simulation file {aircraft_sim_file} not found")
                return
            with open(file_path, 'r') as f:
                simulation_lines = f.readlines()
            simulation_lines = [line.strip() for line in simulation_lines if line.strip()]
            current_line_index = 0
            last_event_time = time.time()
            if not simulation_lines:
                rlog.debug(f"Simulation file {aircraft_sim_file} is empty")
                return
            rlog.debug(f"Loaded {len(simulation_lines)} simulation events from {aircraft_sim_file}")
        except Exception as e:
            rlog.debug(f"Error loading simulation file {aircraft_sim_file}: {e}")
            return
    
    try:
        # Process simulation events
        while True:
            if current_line_index >= len(simulation_lines):
                # Reset to beginning when file ends
                current_line_index = 0
                rlog.debug("Simulation file reset to beginning")
            if current_line_index < len(simulation_lines):
                line = simulation_lines[current_line_index]
                
                # Skip comment lines starting with #
                if line.strip().startswith('#'):
                    current_line_index += 1
                    continue
                
                # Parse line: delay, identifier, lat, lon, alt, track, speed, vspeed
                parts = line.split(',')
                if len(parts) >= 8:
                    try:
                        delay = float(parts[0].strip())
                        identifier = parts[1].strip()
                        latitude = float(parts[2].strip())
                        longitude = float(parts[3].strip())
                        altitude = float(parts[4].strip())
                        track = float(parts[5].strip())
                        speed = float(parts[6].strip())
                        vspeed = float(parts[7].strip())
                        
                        # Wait for the specified delay
                        await asyncio.sleep(delay)
                        # Create simulation data
                        sim_data = {
                            'delay': delay,
                            'identifier': identifier,
                            'latitude': latitude,
                            'longitude': longitude,
                            'altitude': altitude,
                            'track': track,
                            'speed': speed,
                            'vertical_speed': vspeed,
                            'timestamp': time.time()
                        }
                        # Generate appropriate message based on identifier
                        if identifier == "OWNSHIP":
                            # Generate situation message
                            situation_msg = {
                                'GPSLatitude': latitude,
                                'GPSLongitude': longitude,
                                'BaroPressureAltitude': altitude,
                                'GPSTrueCourse': track,
                                'GPSGroundSpeed': speed,
                                'BaroVerticalSpeed': vspeed,
                                'GPSHorizontalAccuracy': 10,
                                'GPSVerticalAccuracy': 10,
                                'GPSFixQuality': 1,
                                'GPSLastFixLocalTime': time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                'GPSLastGPSTimeStratuxTime': time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                'GPSTime': time.strftime("%Y-%m-%dT%H:%M:%SZ")
                            }
                            rlog.log(SITUATION_DEBUG, f"Simulation: Own ship update at {latitude:.6f}, {longitude:.6f}, alt {altitude}ft")
                            # Call new_situation with JSON message
                            radar.new_situation(json.dumps(situation_msg))
                        else:
                            # Generate traffic message
                            traffic_msg = {
                                'Icao_addr': int(identifier, 16) if identifier.startswith("0x") else hash(identifier) & 0xFFFFFF,
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
                                'Last_source': 1  # 1090ES
                            }
                            rlog.log(AIRCRAFT_DEBUG, f"Simulation: Traffic {identifier} at {latitude:.6f}, {longitude:.6f}, alt {altitude}ft")
                            # Call new_traffic with JSON message
                            radar.new_traffic(json.dumps(traffic_msg))
                        current_line_index += 1
                        
                    except (ValueError, IndexError) as e:
                        rlog.debug(f"Error parsing simulation line {current_line_index + 1}: {line} - {e}")
                        current_line_index += 1
                        continue
                else:
                    rlog.debug(f"Invalid simulation line format: {line}")
                    current_line_index += 1
            else:
                await asyncio.sleep(1)  # Wait if no lines available
                
    except asyncio.CancelledError:
        rlog.debug("Simulation handler cancelled")
        return
    except Exception as e:
        rlog.debug(f"Error in simulation handler: {e}")
        return


