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
from globals import rlog, AIRCRAFT_DEBUG

# Threshold to calculate potential collision, warning level low, INFO
COLLISION_THRESHOLD = 180 # in seconds
COLLISION_DIST_THRESHOLD = 2.0
COLLISION_ALT_THRESHOLD = 2000   # aircraft more alt diff than this will not be taken into consideration
# TA thresholds, warning level ADVISORY
TA_THRESHOLD = 40  # TA at 40 seconds
TA_DIST_THRESHOLD = 0.3  # 0.3 mile as threshold for minimum vertical separation on current course
TA_ALT_THRESHOLD = 1500  # 1500 ft threshold for minimal vertical separation currently
# RA_THRESHOLDS, warning level ALARM
RA_THRESHOLD = 25  # RA at 25 seconds
RA_ALT_THRESHOLD = 800 # 1000 ft threshold for minimal vertical currently
RA_DIST_THRESHOLD = 0.2 # 1 nm mile as threshold for minimum vertical separation on current course
# security factors margin
FACTOR_MARGIN = 1.2

# helper functions
def latlon_to_xy_nm(lat_deg, lon_deg, lat_ref_deg, lon_ref_deg):   # calc lat/lon into cartesian coordinates
    dlat = math.radians(lat_deg - lat_ref_deg)
    dlon = math.radians(lon_deg - lon_ref_deg)
    lat_ref_rad = math.radians(lat_ref_deg)
    nm_per_rad = 60.0 * 180.0 / math.pi # 1 rad lat ~ 60 * 180/pi NM
    x = dlat * nm_per_rad
    y = dlon * nm_per_rad * math.cos(lat_ref_rad)
    return x, y



def track_gs_to_vxy(track_deg, gs_kt):   # calc movements based on track and speed
    tr = math.radians(track_deg)
    vy = gs_kt * math.sin(tr)
    vx = gs_kt * math.cos(tr)
    return vx, vy


def tcas_tau(own, intr): # own / intr: dict mit lat, lon, alt_ft, gs_kt, track_deg, vs_fpm
    # find a reference point in the middle
    lat_ref = (own["lat"] + intr["lat"]) / 2.0
    lon_ref = (own["lon"] + intr["lon"]) / 2.0
    rlog.log(AIRCRAFT_DEBUG, f"Reference position: lat = {lat_ref:.3f} lon = {lon_ref:.3f}")
    # calc cartesian coordinates, x means movement North/South, y means movement West/East
    xA, yA = latlon_to_xy_nm(own["lat"], own["lon"], lat_ref, lon_ref)
    xB, yB = latlon_to_xy_nm(intr["lat"], intr["lon"], lat_ref, lon_ref)
    rlog.log(AIRCRAFT_DEBUG, f"Cartesian positions: own ({xA:.1f}/{yA:.1f}), traffic ({xB:.1f}/{yB:.1f})")
    # movement vectors horizontally
    vAx, vAy = track_gs_to_vxy(own["track_deg"], own["gs_kt"])
    vBx, vBy = track_gs_to_vxy(intr["track_deg"], intr["gs_kt"])
    rlog.log(AIRCRAFT_DEBUG, f"Horizontal movement vectors: own ({vAx:.1f}/{vAy:.1f}), traffic ({vBx:.1f}/{vBy:.1f})")
    # relative horizontal
    rx = xB - xA
    ry = yB - yA
    vx = vBx - vAx
    vy = vBy - vAy
    rlog.log(AIRCRAFT_DEBUG, f"Distance horizontal: ({rx:.1f}/{ry:.1f}), Velocity ({vx:.1f}/{vy:.1f})")
    v2 = vx*vx + vy*vy
    rlog.log(AIRCRAFT_DEBUG, f"v2 = {v2:.1f}")

    # horizontal tau and proximity
    tau_hor_sec = float('inf')
    d_cpa_nm = float('inf')
    if v2 > 1e-6:   # do not divide by zero
        dot = rx*vx + ry*vy    # dot < 0 means both target come closer together
        rlog.log(AIRCRAFT_DEBUG, f"dot product = {dot:.1f}")
        tau_h = -dot / v2  # in Stunden
        rlog.log(AIRCRAFT_DEBUG, f"tau in hours = {tau_h}")
        if tau_h > 0.0:
            tau_hor_sec = tau_h * 3600.0
            rlog.log(AIRCRAFT_DEBUG, f"tau = {tau_hor_sec:.2f} seconds")
            # Distance at CPA
            r_cpa_x = rx + vx * tau_h
            r_cpa_y = ry + vy * tau_h
            d_cpa_nm = math.hypot(r_cpa_x, r_cpa_y)

    # vertical tau
    z_rel = intr["alt_ft"] - own["alt_ft"]
    v_rel_z = intr["vs_fpm"] - own["vs_fpm"]

    tau_vert_sec = float('inf')
    if abs(v_rel_z) > 1e-3:
        tau_v_min = - z_rel / v_rel_z
        if tau_v_min > 0.0:
            tau_vert_sec = tau_v_min * 60.0

    return tau_hor_sec, d_cpa_nm, tau_vert_sec


def calc_tcas_state(traffic, situation):
    # Returns a collision classification for the traffic
    # returns a string either: 'unclear', 'RA', 'TA', 'potential_collision', 'no_collision'

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

    # Extract traffic and own data and bring them into unified dict
    own = {
        'lat': situation['latitude'],
        'lon': situation['longitude'],
        'alt_ft': situation['own_altitude'],
        'track_deg': situation['course'],
        'gs_kt': situation['gps_speed'],
        'vs_fpm': situation['vertical_speed']
    }
    traffic = {
        'lat': traffic['Lat'],
        'lon': traffic['Lng'],
        'alt_ft': traffic['Alt'],
        'track_deg': traffic['Track'],
        'gs_kt': traffic['Speed'],
        'vs_fpm': traffic['VSpeed']
    }
    h_diff_ft = abs(own['alt_ft'] - traffic['alt_ft'])

    tau_hor_sec, d_cpa_nm, tau_vert_sec = tcas_tau(own, traffic)
    rlog.log(AIRCRAFT_DEBUG, f"tau_h {tau_hor_sec:.1f} secs, closest proximity {d_cpa_nm:.1f} nm, "
                             f"tau_v {tau_vert_sec:.1f} secs, current height diff {h_diff_ft:.1f} ft")

    # now decide
    # horizontal proximity calculations
    hor_threat_coll = (tau_hor_sec is not float('inf') and 0 < tau_hor_sec <= COLLISION_THRESHOLD and
                     d_cpa_nm is not float('inf') and d_cpa_nm <= COLLISION_DIST_THRESHOLD)
    hor_threat_ta = (tau_hor_sec is not float('inf') and 0 < tau_hor_sec <= TA_THRESHOLD and
                     d_cpa_nm is not float('inf') and d_cpa_nm <= TA_DIST_THRESHOLD)
    hor_threat_ra = (tau_hor_sec is not float('inf') and 0 < tau_hor_sec <= RA_THRESHOLD and
                     d_cpa_nm is not float('inf') and d_cpa_nm <= RA_DIST_THRESHOLD)

    # vertical checks: current height difference ok or convergence in thresholds
    vert_threat_coll = (h_diff_ft <= COLLISION_ALT_THRESHOLD or
                      (tau_vert_sec is not float('inf') and 0 < tau_vert_sec <= COLLISION_THRESHOLD * FACTOR_MARGIN))
    vert_threat_ta = (h_diff_ft <= TA_ALT_THRESHOLD or
                      (tau_vert_sec is not float('inf') and 0 < tau_vert_sec <= TA_THRESHOLD * FACTOR_MARGIN))
    vert_threat_ra = (h_diff_ft <= RA_ALT_THRESHOLD or
                      (tau_vert_sec is not float('inf') and 0 < tau_vert_sec <= RA_THRESHOLD * FACTOR_MARGIN))

    rlog.log(AIRCRAFT_DEBUG, f"Decision matrix, Threat (hor/vert): "
                             f"Collision ({hor_threat_coll}/{vert_threat_coll}), "
                             f"TA ({hor_threat_ta}/{vert_threat_ta}) "
                             f"RA ({hor_threat_ra}/{vert_threat_ra})")

    # no decide, critical decision first
    if hor_threat_ra and vert_threat_ra:   # collision only if horizontal and vertical convergence
        rlog.log(AIRCRAFT_DEBUG, f"Classified as RA situation")
        return 'RA'
    elif hor_threat_ta and vert_threat_ta:
        rlog.log(AIRCRAFT_DEBUG, f"Classified as TA situation")
        return 'TA'
    elif hor_threat_coll and vert_threat_coll:
        rlog.log(AIRCRAFT_DEBUG, f"Classified as potential collision situation")
        return 'pontential_collision'

    rlog.log(AIRCRAFT_DEBUG, f"Classified as no collision situation")
    return 'no_collision'