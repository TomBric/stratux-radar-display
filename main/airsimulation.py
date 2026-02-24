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

# Global variables for simulation state
simulation_file = None
simulation_lines = []
current_line_index = 0
last_event_time = 0.0
last_situation_time = 0.0
last_situation_msg = None

REPEAT_SITUATION_TIME = 2.0     # time in seconds after which the last situation message is repeated

async def sim_handler(aircraft_sim_file, new_traffic_func, new_situation_func):
    global simulation_file, simulation_lines, current_line_index, last_event_time, last_situation_time, last_situation_msg

    await asyncio.sleep(1)  # first wait for the radar to be initialized
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

    # Send initial steering message to set radar parameters
    steering_msg = {
        'RadarRange': 5,
        'RadarLimits': 2000
    }
    rlog.debug("Simulation: Sending initial steering message with RadarRange=5, RadarLimits=2000")
    new_traffic_func(json.dumps(steering_msg))
    next_situation_time = time.time() + REPEAT_SITUATION_TIME
    last_situation_msg = None

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
                if len(parts) < 8:
                    rlog.debug(f"Invalid simulation line format: {line}")
                    current_line_index += 1
                    continue
                try:
                    delay = float(parts[0].strip())
                    identifier = parts[1].strip()
                    latitude = float(parts[2].strip())
                    longitude = float(parts[3].strip())
                    altitude = float(parts[4].strip())
                    track = float(parts[5].strip())
                    speed = float(parts[6].strip())
                    vspeed = float(parts[7].strip())
                    # Extract comment from the rest of the line after the 8th value
                    comment = ""
                    if len(parts) > 8:
                        comment = ",".join(parts[8:]).strip()
                        if comment:
                            rlog.debug(f"Simulation: {identifier} (delay {delay}s): {comment}")
                    actual_time = time.time()
                    next_event_time = actual_time + delay
                    await asyncio.sleep(min(next_event_time-actual_time, next_situation_time-actual_time))

                    if time.time() >= next_event_time:   # event is to be triggered
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
                                'GPSTime': time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                'GPSAltitudeMSL': altitude,
                                'BaroSourceType': 1,
                                'AHRSPitch': 0,
                                'AHRSRoll': 0,
                                'AHRSGyroHeading': track,
                                'AHRSSlipSkid': 0,
                                'AHRSStatus': 0,
                                'AHRSGLoad': 1.0,
                                'AHRSGLoadMax': 1.0,
                                'AHRSGLoadMin': 1.0
                            }
                            rlog.log(SITUATION_DEBUG, f"Simulation: Own ship update at {latitude:.6f}, {longitude:.6f}, alt {altitude}ft")
                            # Store last situation message and time
                            last_situation_msg = situation_msg
                            next_situation_time = time.time() + REPEAT_SITUATION_TIME
                            # Call new_situation with JSON message
                            new_situation_func(json.dumps(situation_msg))
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
                                'Last_source': 1,  # 1090ES
                                'Tail': identifier,
                                'DistanceEstimated': 0
                            }
                            rlog.log(AIRCRAFT_DEBUG, f"Simulation: Traffic {identifier} at {latitude:.6f}, {longitude:.6f}, alt {altitude}ft")
                            # Call new_traffic with JSON message
                            new_traffic_func(json.dumps(traffic_msg))
                        current_line_index += 1
                    else:   # next simulation time reached, resend last situation message
                        if last_situation_msg is not None:
                            rlog.log(SITUATION_DEBUG, "Simulation: Resending last situation message")
                            new_situation_func(json.dumps(last_situation_msg))
                        next_situation_time = time.time() + REPEAT_SITUATION_TIME
                except (ValueError, IndexError) as e:
                    rlog.debug(f"Error parsing simulation line {current_line_index + 1}: {line} - {e}")
                    current_line_index += 1
                    continue
                
    except asyncio.CancelledError:
        rlog.debug("Simulation handler cancelled")
        return
    except Exception as e:
        rlog.debug(f"Error in simulation handler: {e}")
        return


