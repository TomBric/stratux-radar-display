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
import numpy as np
import time
from bayesian_filters.kalman import KalmanFilter


# Threshold to calculate potential collision, warning level low, INFO
COLLISION_THRESHOLD = 180 # in seconds
COLLISION_DIST_THRESHOLD = 1.5
COLLISION_ALT_THRESHOLD = 2000   # aircraft more alt diff than this will not be taken into consideration
# TA thresholds, warning level ADVISORY
TA_THRESHOLD = 40  # TA at 40 seconds
TA_DIST_THRESHOLD = 0.3  # 0.3 mile as threshold for minimum separation on current course
TA_ALT_THRESHOLD = 1500  # 1500 ft threshold for minimal vertical separation currently
# RA_THRESHOLDS, warning level ALARM
RA_THRESHOLD = 25  # RA at 25 seconds
RA_ALT_THRESHOLD = 800 # 1000 ft threshold for minimal vertical currently
RA_DIST_THRESHOLD = 0.2 # 0.2 nm mile as threshold for minimum  separation on current course
# security factors margin
FACTOR_MARGIN = 1.2

# helper functions to transform info into cartesian coordinates
def latlon_to_xy_nm(lat_deg, lon_deg, lat_ref_deg, lon_ref_deg):   # calc lat/lon into cartesian coordinates
    dlat = math.radians(lat_deg - lat_ref_deg)
    dlon = math.radians(lon_deg - lon_ref_deg)
    lat_ref_rad = math.radians(lat_ref_deg)
    nm_per_rad = 60.0 * 180.0 / math.pi # 1 rad lat ~ 60 * 180/pi NM
    y = dlat * nm_per_rad
    x = dlon * nm_per_rad * math.cos(lat_ref_rad)
    return x, y


def track_gs_to_vxy(track_deg, gs_kt):   # calc cartesian movements based on track and speed
    tr = math.radians(track_deg)
    vx = gs_kt * math.sin(tr)
    vy = gs_kt * math.cos(tr)
    return vx, vy


def vertical_tau(alt_ft_own, vs_fpm_own, alt_ft_intr, vs_fpm_intr):
    # Calculate vertical tau (time to vertical intercept) between own and intruder.
    # Returns tau_vert_sec (float, inf if not converging).
    z_rel = alt_ft_intr - alt_ft_own
    v_rel_z = vs_fpm_intr - vs_fpm_own

    tau_vert_sec = float('inf')
    if abs(v_rel_z) > 1e-3:
        # dot_z < 0 means they are converging vertically
        # dot_z = z_rel * v_rel_z. If opposite signs, they converge.
        if (z_rel > 0 and v_rel_z < 0) or (z_rel < 0 and v_rel_z > 0):
            tau_v_min = - z_rel / v_rel_z
            if tau_v_min > 0.0:
                tau_vert_sec = tau_v_min * 60.0
    return tau_vert_sec


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

    # horizontal tau and proximity
    tau_hor_sec = float('inf')
    d_cpa_nm = float('inf')
    if v2 > 1e-6:   # do not divide by zero
        dot = rx*vx + ry*vy    # dot < 0 means both targets come closer together
        tau_h = -dot / v2  # in Stunden
        if tau_h > 0.0:
            tau_hor_sec = tau_h * 3600.0
            # Distance at CPA
            r_cpa_x = rx + vx * tau_h
            r_cpa_y = ry + vy * tau_h
            d_cpa_nm = math.hypot(r_cpa_x, r_cpa_y)

    # vertical tau
    tau_vert_sec = vertical_tau(own["alt_ft"], own["vs_fpm"], intr["alt_ft"], intr["vs_fpm"])

    return tau_hor_sec, d_cpa_nm, tau_vert_sec


def assess_threat(tau_h, d_cpa, tau_v, h_diff):
    # threat classification for aircraft with position and velocity
    # Horizontal threats
    h_ra = (0 < tau_h <= RA_THRESHOLD and d_cpa <= RA_DIST_THRESHOLD)
    h_ta = (0 < tau_h <= TA_THRESHOLD and d_cpa <= TA_DIST_THRESHOLD)
    h_coll = (0 < tau_h <= COLLISION_THRESHOLD and d_cpa <= COLLISION_DIST_THRESHOLD)

    # Vertical threats
    v_ra = (abs(h_diff) <= RA_ALT_THRESHOLD or (0 < tau_v <= RA_THRESHOLD * FACTOR_MARGIN))
    v_ta = (abs(h_diff) <= TA_ALT_THRESHOLD or (0 < tau_v <= TA_THRESHOLD * FACTOR_MARGIN))
    v_coll = (abs(h_diff) <= COLLISION_ALT_THRESHOLD or (0 < tau_v <= COLLISION_THRESHOLD * FACTOR_MARGIN))

    if h_ra and v_ra:
        return 'RA'
    if h_ta and v_ta:
        return 'TA'
    if h_coll and v_coll:
        return 'potential_collision'
    return 'no_collision'

def assess_threat_modes(tau_h, tau_v, h_diff):
    # threat classification for aircraft with modes signal only (distance estimated and vertical velocity)
    # Horizontal threats
    h_ra = (0 < tau_h <= RA_THRESHOLD)
    h_ta = (0 < tau_h <= TA_THRESHOLD)
    h_coll = (0 < tau_h <= COLLISION_THRESHOLD)

    # Vertical threats
    v_ra = (abs(h_diff) <= RA_ALT_THRESHOLD or (0 < tau_v <= RA_THRESHOLD * FACTOR_MARGIN))
    v_ta = (abs(h_diff) <= TA_ALT_THRESHOLD or (0 < tau_v <= TA_THRESHOLD * FACTOR_MARGIN))
    v_coll = (abs(h_diff) <= COLLISION_ALT_THRESHOLD or (0 < tau_v <= COLLISION_THRESHOLD * FACTOR_MARGIN))

    if h_ra and v_ra:
        return 'RA'
    if h_ta and v_ta:
        return 'TA'
    if h_coll and v_coll:
        return 'potential_collision'
    return 'no_collision'


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
    if any(key not in traffic for key in ['Alt', 'Lat', 'Lng', 'Track', 'Speed', 'Vvel']):
        rlog.log(AIRCRAFT_DEBUG,
                 f"Missing full aircraft information either: ['Alt', 'Lat', 'Lng', 'Track', 'Speed', 'Vvel']: aircraft classified as 'unclear'")
        rlog.log(AIRCRAFT_DEBUG, f"Traffic was: {traffic}")
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
        'vs_fpm': traffic['Vvel']
    }
    h_diff_ft = abs(own['alt_ft'] - traffic['alt_ft'])

    tau_hor_sec, d_cpa_nm, tau_vert_sec = tcas_tau(own, traffic)
    rlog.log(AIRCRAFT_DEBUG, f"tau_h {tau_hor_sec:.1f}s, d_cpa {d_cpa_nm:.2f}nm, tau_v {tau_vert_sec:.1f}s, h_diff {h_diff_ft:.0f}ft")

    return assess_threat(tau_hor_sec, d_cpa_nm, tau_vert_sec, h_diff_ft)


def tcas_to_prio(tcas_state):
    # Mapping dictionary for efficient lookup
    state_to_prio = {
        'RA': 1,
        'TA': 2,
        'potential_collision': 3,
        'no_collision': 4,
        'unclear': 0
    }
    
    return state_to_prio.get(tcas_state, 0)  # default to 0 for unknown states


# mode-s only targets, distance estimation and tau calculation
#
# horizontal distance estimation uses a time based kalman filter. Additionally it is "gated" to ignore outliers

def setup_distance_filter(initial_dist):
    # kalman filter state x is: [distance, velocity], measurements z are: [distance], all values in nm
    f = KalmanFilter(dim_x=2, dim_z=1)
    f.x = np.array([[initial_dist], [0.]])
    f.H = np.array([[1., 0.]])    # H is constant, we are only getting distance measurements
    f.R = 1.0    # noise level (was 2.0)
    f.P *= 10.0   # noise level
    return f


def setup_vertical_filter(initial_alt):
    # kalman filter state x is: [altitude, vertical_velocity], measurements z are: [altitude], all values in ft
    f = KalmanFilter(dim_x=2, dim_z=1)
    f.x = np.array([[initial_alt], [0.]])
    f.H = np.array([[1., 0.]])    # H is altitude
    f.R = 50.0   # altitude measurement noise (ft) is minimal, we assume 50 ft here
    f.P *= 100.0  # noise level if aircraft is first detected is high, quick adaption
    return f


def update_traffic_adaptive(ac):
    # used for mode-s only targets, returns distance, velocity, vertical velocity  by using kalman filters for distance and altitude
    # first horizontal distance estimation
    now = time.time()
    last_time = ac.get("last_contact_timestamp", now - 0.5)  # fallback if no last contact timestamp available
    if 'kf' not in ac:   # filter not initialized
        ac['kf'] = setup_distance_filter(ac['DistanceEstimated'])
    dt = max(0.001, now - last_time)  # do not get dt = 0
    rlog.log(AIRCRAFT_DEBUG, f"dt horizontal {dt}")
    
    # Check for potential sign change in velocity to adapt q_var
    # if measurement suggests a different direction than current estimate, increase q_var
    q_var = 1.0
    current_v = ac['kf'].x[1][0]
    innovation = ac['DistanceEstimated'] - ac['kf'].x[0][0]
    if (current_v < -0.1 and innovation > 0.2) or (current_v > 0.1 and innovation < -0.2):
        q_var = 5.0  # boost adaptation for sign change
        rlog.log(AIRCRAFT_DEBUG, "Velocity sign change detected, boosting q_var")

    # update dynamic matrix F mit real dt
    ac['kf'].F = np.array([[1., dt], [0., 1.]])    # new_dist = old_dist + velocity * dt
    # update noiselevel Q according to dt, increase noise with dt
    ac['kf'].Q = np.array([[(dt ** 4) / 4, (dt ** 3) / 2], [(dt ** 3) / 2, (dt ** 2)]]) * q_var
    ac['kf'].predict()
    ac['kf'].update(ac['DistanceEstimated'])
    rlog.log(AIRCRAFT_DEBUG, f"horizontal kalman filter: dist {ac['kf'].x[0][0]} hor-velocity {ac['kf'].x[1][0]}")

    # Update vertical filter
    if 'kf_v' not in ac:
        ac['kf_v'] = setup_vertical_filter(ac['alt'])
        ac['last_used_alt_time'] = ac['last_alt_timestamp']
    # do not update kalman filter if no new altitude is available
    if ac['last_used_alt_time'] == ac['last_alt_timestamp']:
        return ac['kf'].x[0][0], ac['kf'].x[1][0], ac['kf_v'].x[1][0] * 60.0   # dist, velocity, vertical velocity
    # new altitude is available
    dt_v = max(0.001, ac['last_alt_timestamp'] - ac.get('last_used_alt_time', now - 0.5))
    rlog.log(AIRCRAFT_DEBUG, f"dt vertical {dt_v}")
    ac['kf_v'].F = np.array([[1., dt_v], [0., 1.]])
    q_var_v = 10.0  # vertical noise variance
    # update noiselevel Q according to dt, increase noise with dt
    ac['kf_v'].Q = np.array([[(dt_v ** 4) / 4, (dt_v ** 3) / 2], [(dt_v ** 3) / 2, (dt_v ** 2)]]) * q_var_v
    ac['kf_v'].predict()
    ac['kf_v'].update(ac['alt'])
    ac['last_used_alt_time'] = ac['last_alt_timestamp']

    # kf_v.x[1][0] is vertical velocity (ft/s), convert to fpm
    v_fpm = ac['kf_v'].x[1][0] * 60.0

    # distance, velocity, vertical velocity
    return ac['kf'].x[0][0], ac['kf'].x[1][0], v_fpm


def calc_modes_tcas_state(ac, situation):
    if 'own_altitude' not in situation or 'alt' not in ac or 'DistanceEstimated' not in ac:
        return 'unclear'
    if ac['alt'] == 0 or ac['DistanceEstimated'] == 0:
        return 'unclear'

    try:
        dist, v_close, v_fpm = update_traffic_adaptive(ac)
        rlog.log(AIRCRAFT_DEBUG, f"Mode-S: result of kalman filters: ")
        rlog.log(AIRCRAFT_DEBUG, f"  dist {dist} ")
        rlog.log(AIRCRAFT_DEBUG, f"  h_vel {v_close} ")
        rlog.log(AIRCRAFT_DEBUG, f"  v_fpm {v_fpm}")
    except Exception as e:
        rlog.log(AIRCRAFT_DEBUG, f"Mode-S filter error: {e}")
        return 'unclear'

    tau_h = -dist / v_close if v_close < -1e-6 else float('inf')
    tau_v = vertical_tau(situation['own_altitude'], situation['vertical_speed'], ac['alt'], v_fpm)
    h_diff = ac['hdiff'] * 100.0
    rlog.log(AIRCRAFT_DEBUG, f"MODES: dist {dist:.2f}nm, v_close {v_close:.2f}nm/s, tau_h {tau_h:.1f}s, tau_v {tau_v:.1f}s, vspeed {v_fpm:.0f}fpm, h_diff {h_diff:.0f}ft")
    return assess_threat_modes(tau_h, tau_v, h_diff)
