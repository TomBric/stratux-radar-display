#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK
#
# BSD 3-Clause License
# Copyright (c) 2020-2025, Thomas Breitbach
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

# This is the implementation for waveshare 3in7 e-paper display for opening of 3 1/8 inch.
# Does not use full display size, but creates a round display with a diameter of 3.5 inch.
from . import epd3in7
from .. import dcommon
from PIL import Image, ImageDraw, ImageFont
import math
import time
import datetime
from pathlib import Path
import logging


top_index = 0    # top index being displayed in checklist

DISPLAY_OFFSET = -15   # to center display in the 3 1/8 inch instrument hole

class Epaper3in7_Round(dcommon.GenericDisplay):
    # display constants
    VERYLARGE = 48  # timer
    MORELARGE = 36
    LARGE = 30  # size of height indications of aircraft
    SMALL = 24  # size of information indications on top and bottom
    VERYSMALL = 18
    AWESOME_FONTSIZE = 18  # bluetooth indicator
    AIRCRAFT_SIZE = 6  # size of aircraft arrow
    BG_COLOR = "white"
    TEXT_COLOR = "black"
    HIGHLIGHT_COLOR = "black"
    AIRCRAFT_COLOR = "black"
    AIRCRAFT_OUTLINE = "black"
    MODE_S_COLOR = "black"
    MINIMAL_CIRCLE = 20  # minimal size of mode-s circle
    ARCPOSITION_EXCLUDE_FROM = 110
    ARCPOSITION_EXCLUDE_TO = 250
    # AHRS
    AHRS_EARTH_COLOR = "white"  # how ahrs displays the earth
    AHRS_SKY_COLOR = "white"  # how ahrs displays the sky
    AHRS_HORIZON_COLOR = "black"  # how ahrs displays the horizon
    AHRS_MARKS_COLOR = "black"  # color of marks and corresponding text in ahrs
    ANGLE_OFFSET=270 # offset for calculating angles in displays
    device = None
    image = None
    draw = None
    mask = None

    def init(self, fullcircle=False):
        self.device = epd3in7.EPD()
        self.device.init(0)
        self.device.Clear(0xFF, 0)  # necessary to overwrite everything
        self.image = Image.new('1', (self.device.height, self.device.width), 0xFF)
        self.draw = ImageDraw.Draw(self.image)
        self.device.init(1)
        self.device.Clear(0xFF, 1)
        self.sizex = self.device.height
        self.sizey = self.device.width
        self.zerox = self.sizex / 2 + DISPLAY_OFFSET
        if not fullcircle:
            self.zeroy = 200  # not centered
            self.max_pixel = 370
        else:
            self.zeroy = self.sizey / 2
            self.max_pixel = self.sizey
        self.ah_zeroy = int(self.sizey / 2) # zero line for ahrs
        self.ah_zerox = int(self.sizex / 2) + DISPLAY_OFFSET
        # measure time for refresh
        start = time.time()
        # do sync version of display to measure time
        self.device.display_1Gray(self.device.getbuffer_optimized(self.image))
        end = time.time()
        self.display_refresh = end - start
        # compass preparation
        pic_path = str(Path(__file__).resolve().parent.joinpath('plane-white-128x128.bmp'))
        self.compass_aircraft = Image.open(pic_path)
        self.mask = Image.new('1', (self.LARGE * 2, self.LARGE * 2))
        self.cdraw = ImageDraw.Draw(self.mask)
        self.rlog.debug(f'Epaper_3in7_Round: sizex={self.sizex} sizey={self.sizey} zero=({self.zerox}, {self.zeroy}) '
                        f'refresh-time: {str(round(self.display_refresh, 2))} secs')
        return self.max_pixel, self.zerox, self.zeroy, self.display_refresh

    def display(self):
        self.device.async_display_1Gray(self.device.getbuffer_optimized(self.image))

    def is_busy(self):
        return self.device.async_is_busy()

    @staticmethod
    def next_arcposition(old_arcposition, exclude_from=0, exclude_to=0):
        return dcommon.GenericDisplay().next_arcposition(old_arcposition,
            exclude_from=Epaper3in7_Round().ARCPOSITION_EXCLUDE_FROM, exclude_to=Epaper3in7_Round().ARCPOSITION_EXCLUDE_TO)

    def cleanup(self):
        self.device.init(0)
        self.device.Clear(0xFF, 0)
        self.device.sleep()
        self.device.Dev_exit()

    def refresh(self):
        self.device.Clear(0xFF, 0)  # necessary to overwrite everything
        self.device.init(1)

    def startup(self, version, target_ip, seconds):
        logopath = Path(__file__).resolve().parent / 'stratux-logo-192x192.bmp'
        logo = Image.open(logopath)
        self.draw.bitmap((self.zerox - 96, 0), logo, fill=self.TEXT_COLOR)
        self.centered_text(188, f"Radar {version}", self.LARGE)
        self.centered_text(self.sizey - 2 * self.VERYSMALL - 2, f"Connecting to {target_ip}", self.VERYSMALL)
        self.display()
        time.sleep(seconds)

    def situation(self, connected, gpsconnected, ownalt, course, rrange, altdifference, bt_devices, sound_active,
                  gps_quality, gps_h_accuracy, optical_bar, basemode, extsound, co_alarmlevel, co_alarmstring):
        self.draw.ellipse((self.zerox - self.max_pixel // 2, self.zeroy - self.max_pixel // 2,
                           self.zerox + self.max_pixel // 2, self.zeroy + self.max_pixel // 2), outline=self.TEXT_COLOR)
        self.draw.ellipse((self.zerox - self.max_pixel // 4, self.zeroy - self.max_pixel // 4,
                           self.zerox + self.max_pixel // 4, self.zeroy + self.max_pixel // 4), outline=self.TEXT_COLOR)
        self.draw.ellipse((self.zerox - 2, self.zeroy - 2, self.zerox + 2, self.zeroy + 2), outline=self.TEXT_COLOR)
        self.draw.text((5, 1), f"{rrange} nm", font=self.fonts[self.SMALL], fill=self.TEXT_COLOR)

        if gps_quality == 0:
            t = "GPS-NoFix"
        elif gps_quality == 1:
            t = f"3D GPS\n{round(gps_h_accuracy, 1)}m"
        elif gps_quality == 2:
            t = f"DGNSS\n{round(gps_h_accuracy, 1)}m"
        else:
            t = ""
        if basemode:
            t += "\nGround\nmode"
        self.draw.text((5, self.SMALL + 10), t, font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)

        t = f"FL{round(ownalt / 100)}"
        textlength = self.draw.textlength(t, self.fonts[self.SMALL])
        self.draw.text((self.sizex - textlength - 5, self.SMALL + 10), t, font=self.fonts[self.SMALL], fill=self.TEXT_COLOR)

        t = f"{altdifference} ft"
        textlength = self.draw.textlength(t, self.fonts[self.SMALL])
        self.draw.text((self.sizex - textlength - 5, 1), t, font=self.fonts[self.SMALL], fill=self.TEXT_COLOR, align="right")

        self.centered_text(1, f"{course}°", self.SMALL)

        if not gpsconnected:
            self.centered_text(70, "No GPS", self.SMALL)
        if not connected:
            self.centered_text(30, "No Connection!", self.SMALL)
        if co_alarmlevel > 0:
            self.centered_text(250, f"CO Alarm: {co_alarmstring}", self.SMALL)

        if extsound or bt_devices > 0:
            if sound_active:
                t = ""
                if extsound:
                    t += "\uf028"  # volume symbol
                if bt_devices > 0:
                    t += "\uf293"  # bluetooth symbol
            else:
                t = "\uf1f6"  # bell off symbol
            textlength = self.draw.textlength(t, self.awesomefont)
            self.draw.text((self.sizex - textlength - 5, self.sizey - self.SMALL), t,
                           font=self.awesomefont, fill=self.TEXT_COLOR)

        self.draw.line((self.sizex - 8, 80 + optical_bar * 10, self.sizex - 8, 80 + optical_bar * 10 + 8),
                       fill=self.TEXT_COLOR, width=5)

    def gmeter(self, current, maxg, ming, error_message):
        gm_size = 280
        self.meter(current, -3, 5, 110, 430, gm_size, 140, 140, 1, 0.25,      "G-Force", None)
        lines = (
            ("max", f'{maxg:+1.2f}'),
            ("act", f'{current:+1.2f}'),
            ("min", f'{ming:+1.2f}')
        )
        self.dashboard(gm_size+self.SMALL, self.sizey//2 - 5*self.SMALL//2 , self.sizex-gm_size-self.SMALL-5, lines, rounding=True,
                       headline="G-Meter", headline_size=self.SMALL)
        self.bottom_line("", "    Mode", "Reset")

    def vsi(self, vertical_speed, flight_level, gps_speed, gps_course, gps_altitude, vertical_max, vertical_min, error_message):
        self.meter(vertical_speed / 100, -20, 20, 110, 430, self.sizey, self.sizey // 2,
                   self.sizey // 2, 5, 1, "Vertical Speed", "100 feet per min",
                   middle_fontsize=self.VERYSMALL)

        self.draw.text((25, self.sizey // 2 - self.VERYSMALL - 25), "up", font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR, align="left")
        self.draw.text((25, self.sizey // 2 + 25), "dn", font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR, align="left")
        lines = (
            ("act", f"{vertical_speed:+1.0f}"),
            ("max", f"{vertical_max:+1.0f}"),
            ("min", f"{vertical_min:+1.0f}")
        )
        self.dashboard(self.sizey + 5, self.VERYSMALL,
                       self.sizex - self.sizey - 2 * 5, lines, rounding=True, headline="Vert Speed [ft/min]")
        lines = (
            ("Flight-Level", f"{round(flight_level / 100):1.0f}"),
            ("GPS-Alt [ft]", f"{gps_altitude:1.0f}"),
            ("GpsSpd [kts]", f"{gps_speed:1.1f}")
        )
        self.dashboard(self.sizey + 5, self.sizey // 2 ,
                       self.sizex - self.sizey - 2 * 5, lines, rounding=True)

        if error_message:
            self.centered_text(60, error_message, self.LARGE)
        self.bottom_line("", "    Mode", "Reset")

    def earthfill(self, pitch, roll, length, scale):   # possible function for derived classed to implement fillings for earth
        # draws some type of black shading for the earth
        for pm in range(0, -180-1, -3):
            self.draw.line((self.linepoints(pitch, roll, pm, length, scale)), fill="black", width=1)

    def flighttime(self, last_flights, side_offset=0, long_version=False):
        super().flighttime(last_flights, side_offset=35, long_version=True)

    def stratux(self, stat, altitude, gps_alt, gps_quality):
        starty = 0
        self.centered_text(0, f"Stratux {stat['version']}", self.SMALL)
        starty += self.SMALL + 8
        colors = {'outline': 'black', 'black_white_offset': 5}
        bar_start, bar_end = 100, 420

        starty = self.bar(starty, "1090", stat['ES_messages_last_minute'], stat['ES_messages_max'],
                          bar_start, bar_end, colors, side_offset=5, line_offset=10)
        if stat['OGN_connected']:
            starty = self.bar(starty, "OGN", stat['OGN_messages_last_minute'], stat['OGN_messages_max'],
                              bar_start, bar_end, colors, side_offset=5, line_offset=10)
            noise_text = f"{round(stat['OGN_noise_db'], 1)}@{round(stat['OGN_gain_db'], 1)}dB"
            starty = self.bar(starty, "noise", stat['OGN_noise_db'], 25,
                              bar_start, bar_end, colors, side_offset=5, unit="dB", minval=1, valtext=noise_text,
                              line_offset=10)
        if stat['UATRadio_connected']:
            starty = self.bar(starty, "UAT", stat['UAT_messages_last_minute'], stat['UAT_messages_max'],
                              bar_start, bar_end, colors, side_offset=5, line_offset=10)
        if stat['CPUTemp'] > -300:
            starty = self.bar(starty, "temp", round(stat['CPUTemp'], 1), round(stat['CPUTempMax'], 0),
                              bar_start, bar_end, colors, side_offset=5, unit="°C", line_offset=10)

        self.draw.text((5, starty), "GPS hw", font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)
        self.draw.text((bar_start, starty), stat['GPS_detected_type'], font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)
        starty += self.VERYSMALL + 5

        self.draw.text((5, starty), "GPS sol", font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)
        t = "3D GPS " if gps_quality == 1 else "DGNSS " if gps_quality == 2 else ""
        gps = f"{round(stat['GPS_position_accuracy'], 1)}m" if stat['GPS_position_accuracy'] < 19999 else "NoFix"
        self.draw.text((bar_start, starty), t + gps, font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)

        t = f"Sat: {stat['GPS_satellites_locked']} sol/{stat['GPS_satellites_seen']} seen/{stat['GPS_satellites_tracked']} track"
        self.draw.text((220, starty), t, font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)
        starty += self.VERYSMALL + 5

        self.draw.text((5, starty), "altitudes", font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)
        alt = f"{gps_alt:5.0f}" if stat['GPS_position_accuracy'] < 19999 else " ---"
        self.draw.text((bar_start, starty), f"P-Alt {round(altitude)} ft", font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)
        self.draw.text((220, starty), f"Corr {stat['AltitudeOffset']:+} ft", font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)
        self.draw.text((340, starty), f"GPS-Alt {alt} ft", font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)
        starty += self.VERYSMALL + 5

        self.draw.text((5, starty), "sensors", font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)
        x = self.round_text(100, starty, "IMU", yesno=stat['IMUConnected'], out_color=self.TEXT_COLOR)
        self.round_text(x, starty, "BMP", yesno=stat['BMPConnected'], out_color=self.TEXT_COLOR)
        self.bottom_line("+10 ft", "Mode", "-10 ft")

    def cowarner(self, co_values, co_max, r0, timeout, alarmlevel, alarmtext, simulation_mode=False):
        self.centered_text(0, alarmtext, self.LARGE)
        graphpos = (0,40)
        graphsize = (300, 200)
        self.graph(graphpos, graphsize, co_values, 0, 120, timeout, value_line1=50, value_line2=100,
                   glinewidth=3, linewidth=3)
        lines = [
            ("Warnlevel:", f"{alarmlevel:3d}"),
            ("",""),
            ("CO act:", f"{co_values[-1]:3d}") if co_values else ("CO act:", "---"),
            ("CO max:", f"{co_max:3d}"),
            ("", ""),
            ("", ""),
            ("R0", f"{r0 / 1000:.1f}k")
        ]
        loffset = 320  # start of text
        roffset = 10
        self.dashboard(loffset, 40 + self.VERYSMALL, self.sizex - loffset - roffset, lines)
        if simulation_mode:
            self.round_text(self.sizex//4, self.sizey//3, "simulation mode", out_color=self.TEXT_COLOR)
        self.bottom_line("Calibrate", "Mode", "Reset")

    def distance(self, now, gps_valid, gps_quality, gps_h_accuracy, distance_valid, gps_distance, gps_speed, baro_valid,
                         own_altitude, alt_diff, alt_diff_takeoff, vert_speed, ahrs_valid, ahrs_pitch, ahrs_roll,
                         ground_distance_valid, grounddistance, error_message):
        offset = 5
        self.centered_text(0, "GPS Distance", self.SMALL)
        lines = [
            ("Date", f"{now.day:02d}.{now.month:02d}.{now.year:04d}"),
            ("UTC", f"{now.hour:02d}:{now.minute:02d}:{now.second:02d},{now.microsecond // 100000:1d}")
        ]
        starty = self.dashboard(offset, self.SMALL, self.zerox - offset, lines, headline="Date/Time", rounding=True)

        t, accuracy = "GPS-NoFix", ""
        if gps_quality == 1:
            t, accuracy = "3D GPS", f"{gps_h_accuracy:.1f}m"
        elif gps_quality == 2:
            t, accuracy = "DGNSS", f"{gps_h_accuracy:.1f}m"
        gps_dist_str = f"{gps_distance:.0f}" if distance_valid else "---"
        gps_speed_str = f"{gps_speed:.1f}" if gps_valid else "---"
        lines = [
            ("GPS-Distance [m]", gps_dist_str),
            ("GPS-Speed [kts]", gps_speed_str),
            (t, accuracy)
        ]
        starty = self.dashboard(offset, starty, self.zerox - offset, lines, headline="GPS", rounding=True)

        if ground_distance_valid:
            lines = [("Grd Dist [cm]", f"{grounddistance / 10:+.1f}")]
            self.dashboard(offset, starty, self.zerox - offset, lines, headline="Ground Sensor", rounding=True)

        starty = self.SMALL
        if ahrs_valid:
            lines = [
                ("Pitch [deg]", f"{ahrs_pitch:+2d}"),
                ("Roll [deg]", f"{ahrs_roll:+2d}")
            ]
            starty = self.dashboard(self.zerox + offset, starty, self.zerox - 2 * offset, lines, headline="AHRS", rounding=True)
        if baro_valid:
            takeoff_str = f"{alt_diff_takeoff:+5.1f}" if alt_diff_takeoff is not None else "---"
            alt_diff_str = f"{alt_diff:+5.1f}" if alt_diff is not None else "---"
            lines = [
                ("Baro-Altitude [ft]", f"{own_altitude:.0f}"),
                ("Vert Speed [ft]", f"{vert_speed:+4.0f}"),
                ("Ba-Diff r-up [ft]", alt_diff_str),
                ("Ba-Diff tof [ft]", takeoff_str)
            ]
            self.dashboard(self.zerox + offset, starty, self.zerox - 2 * offset, lines, headline="Baro", rounding=True)
        if error_message:
            self.centered_text(self.sizey // 4, error_message, self.LARGE)
        self.bottom_line("Stats/Set", "Mode", "Start")

    def distance_statistics(self, values, gps_valid, gps_altitude, dest_altitude, dest_alt_valid, ground_warnings):
        self.centered_text(0, "Start-/Landing Statistics", self.SMALL)

        st = '---'
        if 'start_time' in values:
            st = values['start_time'].strftime("%H:%M:%S,%f")[:-5]
        lines = [
            ("t-off time", st),
            ("t-off alt [ft]", self.form_line(values, 'start_altitude', "{:5.1f}")),
            ("t-off dist [m]", self.form_line(values, 'takeoff_distance', "{:3.1f}")),
            ("obst dist [m]", self.form_line(values, 'obstacle_distance_start', "{:3.1f}")),
        ]
        self.dashboard(5, 35, 225, lines, headline="Takeoff", rounding=True)
        lt = '---'
        if 'landing_time' in values:
            lt = values['landing_time'].strftime("%H:%M:%S,%f")[:-5]
        lines = [
            ("ldg time", lt),
            ("ldg alt [ft]", self.form_line(values, 'landing_altitude', "{:5.1f}")),
            ("ldg dist [m]", self.form_line(values, 'landing_distance', "{:3.1f}")),
            ("obst dist [m]", self.form_line(values, 'obstacle_distance_landing', "{:3.1f}")),
        ]
        starty = self.dashboard(250, 35, 225, lines, headline="Landing", rounding=True)
        if ground_warnings:
            dest_alt_str = f"{dest_altitude:+5.0f}" if dest_alt_valid else "---"
            gps_alt_str = f"{gps_altitude:+5.0f}" if gps_valid else "---"
            lines = [
                ("Act GPS-Alt [ft]", gps_alt_str),
                ("Destination Alt [ft]", dest_alt_str),
            ]
            self.dashboard(5, starty + 10, 475, lines, headline="Destination Elevation", rounding=True)

        if not ground_warnings:
            self.bottom_line("", "Back", "")
        else:
            self.bottom_line("+/-100ft", "  Back", "+/-10ft")


# instantiate a single object in the file, needs to be done and inherited in every display module
radar_display = Epaper3in7_Round()