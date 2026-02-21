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

import math
import logging
from globals import rlog, AIRCRAFT_DEBUG

# Threshold to calculate potential collision
COLLISION_THRESHOLD = 180 # in seconds
# Thresholds for TA and RA as defined by ICAO for General Aviation below 10000 ft
TA_THRESHOLD = 40  # TA at 40 seconds
RA_THRESHOLD = 25  # RA at 25 seconds
RA_ALT_THRESHOLD = 1000 # 1000 ft threshold for minimal vertical separation on current vertical movements
RA_DIST_THRESHOLD = 1.0 # 1 nm mile as threshold for minimum vertical separation on current course
TA_DIST_THRESHOLD = 2.0  # 2 nm mile as threshold for minimum vertical separation on current course
TA_ALT_THRESHOLD = 1500  # 1500 ft threshold for minimal vertical separation on current vertical movements
# this means tau will be calculated the thresholds are underrun when calculating current
# movements of own and other aircraft

def calc_tcas_state(traffic, distance, bearing, situation):
    # Returns a collision classification for the traffic
    # returns a string either: 'RA', 'TA', 'unclear', 'potential_collision', 'no_collision'

    # first check if all data is available otherwise return unclear
    if not situation['gps_active'] or situation['gps_speed'] <= 0:
        rlog.log(AIRCRAFT_DEBUG, f"No own gps signal: aircraft classified as 'unclear'")
        return 'unclear'
    if any(key not in situation for key in ['own_altitude', 'vertical_speed']):
        rlog.log(AIRCRAFT_DEBUG, f"Missing situation information about 'own_altitude' and 'vertical speed': aircraft classified as 'unclear'")
        return 'unclear'
    if any(key not in traffic for key in ['Alt', 'Lat', 'Lng', 'Track', 'Speed', 'VSpeed']):
        rlog.log(AIRCRAFT_DEBUG,
                 f"Missing full aircraft information either: ['Alt', 'Lat', 'Lng', 'Track', 'Speed', 'VSpeed']: aircraft classified as 'unclear'")
        return 'unclear'

    # Extract traffic data
    own_alt = situation['own_altitude']
    own_vspeed = situation['vertical_speed']
    traffic_alt = traffic['Alt']
    traffic_course = traffic['Track']
    traffic_speed = traffic['Speed']
    traffic_vspeed = traffic['VSpeed']

    # Calculate height difference
    height_diff = abs(traffic_alt - own_alt)

    # Calculate vertical tau (time to height convergence)
    rel_vspeed = traffic_vspeed - own_vspeed
    vertical_tau = float('inf')
    if abs(rel_vspeed) > 0.1:  # Avoid division by very small numbers
        # Time until vertical separation becomes zero
        vertical_tau = abs(height_diff / rel_vspeed) * 60  # Convert to seconds
        rlog.log(AIRCRAFT_DEBUG, f"Vertical tau: {vertical_tau} seconds")

    # Own speed and course
    own_speed = situation['gps_speed']
    own_course = situation['course']

    # Convert vectors to cartesian coordinates
    # vector components of traffic and own
    own_vx = own_speed * math.sin(math.radians(own_course))
    own_vy = own_speed * math.cos(math.radians(own_course))
    traffic_vx = traffic_speed * math.sin(math.radians(traffic_course))
    traffic_vy = traffic_speed * math.cos(math.radians(traffic_course))
    # Relative velocity
    rel_vx = traffic_vx - own_vx
    rel_vy = traffic_vy - own_vy
    rel_speed = math.sqrt(rel_vx ** 2 + rel_vy ** 2)
    rlog.log(AIRCRAFT_DEBUG, f"Relative speed: {rel_speed:.1f} knots")
    if rel_speed < 0.1:  # knots, if relative speed very small, no convergence
        rlog.log(AIRCRAFT_DEBUG, f"Relative speed smaller 0.1 kts. Aircraft classified as 'no_collision'")
        return 'no_collision'

    # Position vectors (simplified for short distances)
    # Assumption: target_x, target_y from bearing and distance
    target_x = distance * math.sin(math.radians(bearing))
    target_y = distance * math.cos(math.radians(bearing))
    # Calculate Tau: time to minimum distance
    dot_product = -(target_x * rel_vx + target_y * rel_vy)  # tau = -(r · v_rel) / |v_rel|²
    if dot_product <= 0:
        rlog.log(AIRCRAFT_DEBUG, f"Dot product={dot_product:.1f} is <=0, targets diverging or abeam. Aircraft classified as 'no_collision'")
        return 'no_collision'  # Targets are diverging or abeam
    tau_time = dot_product / (rel_speed ** 2) * 3600  # Convert to seconds
    rlog.log(AIRCRAFT_DEBUG, f"Tau time (projected time for closest approach): {tau_time:.1f} seconds")
    # Calculate minimum distance at tau
    min_dist_x = target_x + rel_vx * tau_time / 3600
    min_dist_y = target_y + rel_vy * tau_time / 3600
    min_distance = math.sqrt(min_dist_x ** 2 + min_dist_y ** 2)
    rlog.log(AIRCRAFT_DEBUG, f"Minimum distance at closest approach): {min_distance:.1f} nm")

    # ICAO TCAS Advisory Classification - based purely on tau and distance criteria
    if 0 < tau_time <= RA_THRESHOLD: # Check for Resolution Advisory (RA) conditions
        if min_distance < RA_DIST_THRESHOLD:  # Within minimum distance for RA
            # Check vertical convergence timing
            if vertical_tau != float('inf'):
                time_diff = abs(tau_time - vertical_tau)
                if time_diff <= RA_THRESHOLD:  # Within 10 seconds for RA
                    rlog.log(AIRCRAFT_DEBUG, f"time diff of tau_time and vertical_tau: {time_diff:.1f} nm. Classified as 'RA'")
                    return 'RA'
            else:
                # No vertical convergence, but check if already in close proximity
                if height_diff <= RA_ALT_THRESHOLD:  # Within threshold for RA
                    rlog.log(AIRCRAFT_DEBUG,f"Height diff {height_diff:.1f} smaller than RA_ALT_THRESHOLD. Classified as 'RA'")
                    return 'RA'
    # Check for Traffic Advisory (TA) conditions
    elif 0 < tau_time <= TA_THRESHOLD: # Check for Traffic Advisory (TA) conditions
        if min_distance < TA_DIST_THRESHOLD:  # Within 2 NM minimum distance for TA
            # Check vertical convergence timing
            if vertical_tau != float('inf'):
                time_diff = abs(tau_time - vertical_tau)
                if time_diff <= TA_THRESHOLD:  # Within 20 seconds for TA
                    rlog.log(AIRCRAFT_DEBUG, f"time diff of tau_time and vertical_tau: {time_diff:.1f} nm. Classified as 'TA'")
                    return 'TA'
            else:
                # No vertical convergence, but check if already in proximity
                if height_diff <= TA_ALT_THRESHOLD:  # Within 1500 feet for TA
                    rlog.log(AIRCRAFT_DEBUG,f"Height diff {height_diff:.1f} smaller than TA_ALT_THRESHOLD. Classified as 'TA'")
                    return 'TA'

    # Check for potential collision (close but not yet at TA/RA thresholds)
    if 0 < tau_time <= COLLISION_THRESHOLD:  # collision threshold
        rlog.log(AIRCRAFT_DEBUG, f"Tau time {tau_time:.1f} smaller than COLLISION_THRESHOLD. Classified as 'potential_collision'")
        return 'potential_collision'
    # No collision risk
    rlog.log(AIRCRAFT_DEBUG,"Tau time {tau_time:.1f} secondes. Classified as 'no_collision'")
    return 'no_collision'
