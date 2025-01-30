#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK
#
# BSD 3-Clause License
# Copyright (c) 2020, Thomas Breitbach
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

from . import epd3in7
from .. import dcommon
from PIL import Image, ImageDraw, ImageFont
import math
import time
import datetime
from pathlib import Path
import logging


top_index = 0    # top index being displayed in checklist

class Epaper3in7(dcommon.GenericDisplay):
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
    AIRCRAFT_COLOR = "black"
    MINIMAL_CIRCLE = 20  # minimal size of mode-s circle
    ARCPOSITION_EXCLUDE_FROM = 110
    ARCPOSITION_EXCLUDE_TO = 250
    # AHRS
    AHRS_EARTH_COLOR = "white"  # how ahrs displays the earth
    AHRS_SKY_COLOR = "white"  # how ahrs displays the sky
    AHRS_HORIZON_COLOR = "black"  # how ahrs displays the horizon
    AHRS_MARKS_COLOR = "black"  # color of marks and corresponding text in ahrs

    CM_SIZE = 15  # size of markings in ahrs


    CO_SPACE = 3
    ANGLE_OFFSET=270 # offset for calculating angles in displays


    def init(self, fullcircle=False):
        self.device = epd3in7.EPD()
        self.device.init(0)
        self.device.Clear(0xFF, 0)  # necessary to overwrite everything
        self.epaper_image = Image.new('1', (self.device.height, self.device.width), 0xFF)
        self.draw = ImageDraw.Draw(self.epaper_image)
        self.device.init(1)
        self.device.Clear(0xFF, 1)
        self.sizex = self.device.height
        self.sizey = self.device.width
        self.zerox = self.sizex / 2
        if not fullcircle:
            self.zeroy = 200  # not centered
            self.max_pixel = 400
        else:
            self.zeroy = self.sizey / 2
            self.max_pixel = self.sizey
        self.ah_zeroy = int(self.sizey / 2) # zero line for ahrs
        self.ah_zerox = int(self.sizex / 2)
        # measure time for refresh
        start = time.time()
        # do sync version of display to measure time
        self.device.display_1Gray(self.device.getbuffer_optimized(self.epaper_image))
        end = time.time()
        self.display_refresh = end - start
        # compass preparation
        pic_path = str(Path(__file__).resolve().parent.joinpath('plane-white-128x128.bmp'))
        self.compass_aircraft = Image.open(pic_path)
        self.mask = Image.new('1', (self.LARGE * 2, self.LARGE * 2))
        self.cdraw = ImageDraw.Draw(self.mask)
        self.rlog.debug(f'Epaper_3in7 selected: sizex={self.sizex} sizey={self.sizey} zero=({self.zerox}, {self.zeroy}) '
                        f'refresh-time: {str(round(self.display_refresh, 2))} secs')
        return self.max_pixel, self.zerox, self.zeroy, self.display_refresh

    def display(self):
        self.device.async_display_1Gray(self.device.getbuffer_optimized(self.epaper_image))

    def is_busy(self):
        return self.device.async_is_busy()

    @staticmethod
    def next_arcposition(old_arcposition):
        return dcommon.GenericDisplay().next_arcposition(old_arcposition,
            exclude_from=Epaper3in7().ARCPOSITION_EXCLUDE_FROM, exclude_to=Epaper3in7().ARCPOSITION_EXCLUDE_TO)

    def cleanup(self):
        self.device.init(0)
        self.device.Clear(0xFF, 0)
        self.device.sleep()
        self.device.Dev_exit()

    def refresh(self):
        self.device.Clear(0xFF, 0)  # necessary to overwrite everything
        self.device.init(1)

    def clear(self):
        self.draw.rectangle((0, 0, self.sizex - 1, self.sizey - 1), fill="white")  # clear everything in image

    def startup(self, version, target_ip, seconds):
        logopath = str(Path(__file__).resolve().parent.joinpath('stratux-logo-192x192.bmp'))
        logo = Image.open(logopath)
        self.draw.bitmap((self.zerox-192/2, 0), logo, fill= self.TEXT_COLOR)
        versionstr = "Radar " + version
        self.centered_text(188, versionstr, self.fonts[self.LARGE])
        self.centered_text(self.sizey - 2 *  self.VERYSMALL - 2, "Connecting to " + target_ip, self.fonts[self.VERYSMALL])
        self.display()
        time.sleep(seconds)


    def situation(self, connected, gpsconnected, ownalt, course, range, altdifference, bt_devices, sound_active,
                  gps_quality, gps_h_accuracy, optical_bar, basemode, extsound, co_alarmlevel, co_alarmstring):
        self.draw.ellipse((self.zerox-self.max_pixel/2, self.zeroy-self.max_pixel/2,
                           self.zerox+self.max_pixel/2, self.zeroy+self.max_pixel/2), outline= self.TEXT_COLOR)
        self.draw.ellipse((self.zerox-self.max_pixel/4, self.zeroy-self.max_pixel/4,
                           self.zerox+self.max_pixel/4, self.zeroy+self.max_pixel/4), outline= self.TEXT_COLOR)
        self.draw.ellipse((self.zerox-2, self.zeroy-2, self.zerox+2, self.zeroy+2), outline= self.TEXT_COLOR)
        self.draw.text((5, 1), str(range)+" nm", font=self.fonts[self.SMALL], fill= self.TEXT_COLOR)
        if gps_quality == 0:
            t = "GPS-NoFix"
        elif gps_quality == 1:
            t = "3D GPS\n" + str(round(gps_h_accuracy, 1)) + "m"
        elif gps_quality == 2:
            t = "DGNSS\n" + str(round(gps_h_accuracy, 1)) + "m"
        else:
            t = ""
        if basemode:
            t += "\nGround\nmode"
        self.draw.text((5, self.SMALL+10), t, font=self.fonts[self.VERYSMALL], fill= self.TEXT_COLOR)

        t = "FL"+str(round(ownalt / 100))
        textlength = self.draw.textlength(t, self.fonts[self.SMALL])
        self.draw.text((self.sizex - textlength - 5, self.SMALL+10), t, font=self.fonts[self.VERYSMALL], fill= self.TEXT_COLOR)

        t = str(altdifference) + " ft"
        textlength = self.draw.textlength(t, self.fonts[self.SMALL])
        self.draw.text((self.sizex - textlength - 5, 1), t, font=self.fonts[self.SMALL], fill= self.TEXT_COLOR, align="right")

        text = str(course) + '°'
        self.centered_text(1, text, self.fonts[self.SMALL])

        if not gpsconnected:
            self.centered_text(70, "No GPS", self.fonts[self.SMALL])
        if not connected:
            self.centered_text(30, "No Connection!", self.fonts[self.SMALL])
        if co_alarmlevel > 0:
            self.centered_text(250, "CO Alarm: " + co_alarmstring, self.fonts[self.SMALL])

        if extsound or bt_devices > 0:
            if sound_active:
                t = ""
                if extsound:
                    t += "\uf028"  # volume symbol
                if bt_devices > 0:
                    t += "\uf293"  # bluetooth symbol
            else:
                t = "\uf1f6"  # bell off symbol
            textlength = self.draw.textlength(t, awesomefont)
            self.draw.text((self.sizex - textlength - 5, self.sizey - self.SMALL), t,
                           font=self.awesomefont, fill= self.TEXT_COLOR)

        # optical keep alive bar at right side
        self.draw.line((self.sizex-8, 80+optical_bar*10, self.sizex-8, 80+optical_bar*10+8), fill= self.TEXT_COLOR, width=5)

    def gmeter(self, current, maxg, ming, error_message):
        gm_size = 280
        self.meter(current, -3, 5, 110, 430, gm_size, 140, 140, 1, 0.25,      "G-Force", None, "black", "black")

        right_center_x = (self.sizex-gm_size)/2+gm_size    # center of remaining part
        lines = (
            ("max", f'{maxg:+1.2f}'),
            ("act", f'{current:+1.2f}'),
            ("min", f'{ming:+1.2f}')
        )
        self.dashboard(gm_size, 0, self.sizex - gm_size, lines, rounding=True, headline="G-Meter")
        self.bottom_line("", "    Mode", "Reset")


    def vsi(self, vertical_speed, flight_level, gps_speed, gps_course, gps_altitude, vertical_max, vertical_min, error_message):
        self.meter(vertical_speed / 100, -20, 20, 110, 430, self.sizey, self.sizey // 2,
                   self.sizey // 2, 5, 1, "Vertical Speed", "100 feet per min",
                   middle_fontsize=self.VERYSMALL)

        self.draw.text((25, self.sizey // 2 - self.VERYSMALL - 25), "up", font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR, align="left")
        self.draw.text((25, self.sizey // 2 + 25), "dn", font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR, align="left")


        # middle_text = "Vertical Speed"
        # tl = self.draw.textlength(middle_text, self.fonts[self.SMALL])
        # self.draw.text((self.sizey / 2 - tl / 2, self.sizey / 2 - self.VERYSMALL - 10), middle_text, font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR, align="left")

        # middle_text = "100 feet per min"
        # tl = self.draw.textlength(middle_text, self.fonts[self.SMALL])
        # self.draw.text((self.sizey / 2 - tl / 2, self.sizey / 2 + 10), middle_text, font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR, align="left")

        # right data display
        self.draw.text((300, 10), "Vert Speed [ft/min]", font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR, align="left")
        self.draw.text((330, 31), "act", font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR, align="left")
        self.draw.text((330, 55), "max", font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR, align="left")
        self.draw.text((330, 79), "min", font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR, align="left")

        self.right_text(28, f"{vertical_speed:+1.0f}", self.fonts[self.SMALL], color=self.TEXT_COLOR)
        self.right_text(52, f"{vertical_max:+1.0f}", self.fonts[self.SMALL], color=self.TEXT_COLOR)
        self.right_text(76, f"{vertical_min:+1.0f}", self.fonts[self.SMALL], color=self.TEXT_COLOR)

        self.draw.text((300, 163), "Flight-Level", font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR, align="left")
        self.right_text(160, f"{round(flight_level / 100):1.0f}", self.fonts[self.SMALL], color=self.TEXT_COLOR)
        self.draw.text((300, 187), "GPS-Alt [ft]", font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR, align="left")
        self.right_text(184, f"{gps_altitude:1.0f}", self.fonts[self.SMALL], color=self.TEXT_COLOR)
        self.draw.text((300, 211), "GpsSpd [kts]", font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR, align="left")
        self.right_text(208, f"{gps_speed:1.1f}", self.fonts[self.SMALL], color=self.TEXT_COLOR)

        if error_message:
            self.centered_text(60, error_message, self.verylargefont)

        self.bottom_line("", "    Mode", "Reset")

    def shutdown(self, countdown, shutdownmode):
        if shutdownmode == 0:   # shutdown stratux + display
            message = "Shutdown stratux & display"
        elif shutdownmode == 1:
            message = "Shutdown display"
        else:
            message = "Reboot"
        centered_text(10, message, self.fonts[self.LARGE])
        message = "in " + str(countdown) + " seconds!"
        centered_text(40, message, self.fonts[self.LARGE])
        message = "Press left button to cancel ..."
        centered_text(110, message, self.fonts[self.SMALL])
        message = "Press middle for display only ..."
        centered_text(140, message, self.fonts[self.SMALL])
        message = "Press right for reboot all ..."
        centered_text(170, message, self.fonts[self.SMALL])

        bottom_line("Cancel", "Display only", "Reboot")

    def earthfill(self, pitch, roll, length, scale):   # possible function for derived classed to implement fillings for earth
        # draws some type of black shading for the earth
        for pm in range(0, -180-1, -3):
            self.draw.line((self.linepoints(pitch, roll, pm, length, scale)), fill="black", width=1)


    def screen_input(headline, subline, text, left, middle, right, prefix, inp, suffix):
        centered_text(0, headline, self.fonts[self.LARGE])
        txt_starty = self.LARGE
        if subline is not None:
            centered_text(LARGE, subline, self.fonts[self.SMALL])
            txt_starty += self.LARGE
        bbox = draw.textbbox((0, txt_starty), text, font=smallfont)
        self.draw.text((0, txt_starty), text, font=smallfont, fill=self.TEXT_COLOR)
        bbox_p = draw.textbbox((bbox[0], bbox[3]), prefix, font=smallfont)
        self.draw.text((bbox[0], bbox[3]), prefix, fill=self.TEXT_COLOR, font=smallfont)
        bbox_rect = draw.textbbox((bbox_p[2], bbox[3]), inp, font=smallfont)
        self.draw.rectangle(bbox_rect, fill="black")
        self.draw.text((bbox_rect[0], bbox[3]), inp, font=smallfont, fill="white")
        self.draw.text((bbox_rect[2], bbox[3]), suffix, font=smallfont, fill=self.TEXT_COLOR)

        bottom_line(left, middle, right)


    def bar(y, text, val, max_val, yellow, red, unit="", valtext=None, minval=0):
        bar_start = 100
        bar_end = 420

        draw.text((5, y), text, font=verysmallfont, fill= self.TEXT_COLOR, align="left")
        right_val = str(int(max_val)) + unit
        textlength = draw.textlength(right_val, self.fonts[self.SMALL])
        draw.text((sizex - textlength - 5, y), right_val, font=verysmallfont, fill= self.TEXT_COLOR, align="right")
        draw.rounded_rectangle([bar_start-2, y-2, bar_end+2, y+VERYSMALL+2], radius=3, fill=None, outline= self.TEXT_COLOR, width=1)
        color =  self.TEXT_COLOR
        if val < minval:
            val = minval   # to display a minimum bar, valtext should be provided in this case
        if max_val != 0:
            xval = bar_start + (bar_end - bar_start) * val / max_val
        else:
            xval = bar_start
        for b in range(int(bar_start), int(xval), 5):
            draw.line([(b, y), (b, y+VERYSMALL)], fill= self.TEXT_COLOR, width=1)
        # draw.rectangle([bar_start, y, xval, y+VERYSMALL], fill=color, outline=None)
        if valtext is not None:
            t = valtext
        else:
            t = str(val)
        tl = draw.textlength(t, self.fonts[self.SMALL])
        draw.text(((bar_end-bar_start)/2+bar_start-tl/2, y), t, font=verysmallfont, fill= self.TEXT_COLOR,
                  stroke_width=1, stroke_fill="white")
        return y+self.VERYSMALL+12

    def flighttime(self, last_flights, side_offset=0):
        super().flighttime(last_flights, 25)


    def round_text(self, x, y, text, bg_color=None, yesno=True, out_color=None):
        # bg color is color of background, if none given, this is the normal background for this display
        # out_color is coler of outline, if none given, outline is not
        # if yesno is false, the text is crossed out
        bg_color = bg_color or self.BG_COLOR
        tl = self.draw.textlength(text, self.fonts[self.SMALL])
        self.draw.rounded_rectangle([x, y, x + tl, y + self.VERYSMALL + 2], radius=4, fill=bg_color)
        if out_color is not None:
            self.draw.rounded_rectangle([x, y, x + tl, y + self.VERYSMALL + 2], radius=4, outline=out_color)
        self.draw.text((x + self.VERYSMALL//2, y), text, font=self.fonts[self.VERYSMALL], fill= self.TEXT_COLOR)
        if not yesno:
            self.draw.line([x, y+self.VERYSMALL+2, x+tl+10, y], fill= self.TEXT_COLOR, width=2)
        return x+tl+20


    def stratux(stat, altitude, gps_alt, gps_quality):
        starty = 0
        centered_text(0, "Stratux " + stat['version'], self.fonts[self.SMALL])
        starty +=  self.SMALL+8
        starty = bar(starty, "1090", stat['ES_messages_last_minute'], stat['ES_messages_max'], 0, 0)
        if stat['OGN_connected']:
            starty = bar(starty, "OGN", stat['OGN_messages_last_minute'], stat['OGN_messages_max'], 0, 0)
            noise_text = str(round(stat['OGN_noise_db'], 1)) + "@" + str(round(stat['OGN_gain_db'], 1)) + "dB"
            starty = bar(starty, "noise", stat['OGN_noise_db'], 25, 12, 18, unit="dB", minval=1, valtext=noise_text)
        if stat['UATRadio_connected']:
            starty = bar(starty, "UAT", stat['UAT_messages_last_minute'], stat['UAT_messages_max'], 0, 0)
        if stat['CPUTemp'] > -300:    # -300 means no value available
            starty = bar(starty, "temp", round(stat['CPUTemp'], 1), round(stat['CPUTempMax'], 0), 70, 80, "°C")
        # GPS
        draw.text((5, starty), "GPS hw", font=verysmallfont, fill= self.TEXT_COLOR)
        draw.text((100, starty), stat['GPS_detected_type'], font=verysmallfont, fill= self.TEXT_COLOR)
        starty +=  self.VERYSMALL + 5
        draw.text((5, starty), "GPS sol", font=verysmallfont, fill= self.TEXT_COLOR)
        if gps_quality == 1:
            t = "3D GPS "
        elif gps_quality == 2:
            t = "DGNSS "
        else:
            t = ""
        if stat['GPS_position_accuracy'] < 19999:
            gps = str(round(stat['GPS_position_accuracy'], 1)) + "m"
        else:
            gps = "NoFix"
        draw.text((100, starty), t + gps, font=verysmallfont, fill= self.TEXT_COLOR)

        t = "Sat: " + str(stat['GPS_satellites_locked']) + " sol/" + \
            str(stat['GPS_satellites_seen']) + " seen/" + str(stat['GPS_satellites_tracked']) + " track"
        draw.text((220, starty), t, font=verysmallfont, fill= self.TEXT_COLOR)

        starty +=  self.VERYSMALL+5

        draw.text((5, starty), "altitudes", font=verysmallfont, fill= self.TEXT_COLOR)
        if stat['GPS_position_accuracy'] < 19999:
            alt = '{:5.0f}'.format(gps_alt)
        else:
            alt = " ---"
        t = "P-Alt {0} ft".format(round(altitude))
        draw.text((100, starty), t, font=verysmallfont, fill= self.TEXT_COLOR)
        t = "Corr {0:+} ft".format(stat['AltitudeOffset'])
        draw.text((220, starty), t, font=verysmallfont, fill= self.TEXT_COLOR)
        t = "GPS-Alt " + alt + " ft"
        draw.text((340, starty), t, font=verysmallfont, fill= self.TEXT_COLOR)
        starty +=  self.VERYSMALL + 5
        draw.text((5, starty), "sensors", font=verysmallfont, fill= self.TEXT_COLOR)
        x = round_text(100, starty, "IMU", "white", stat['IMUConnected'], out= self.TEXT_COLOR)
        round_text(x, starty, "BMP", "white", stat['BMPConnected'], out= self.TEXT_COLOR)
        bottom_line("+10 ft", "Mode", "-10 ft")

    def cowarner(co_values, co_max, r0, timeout, alarmlevel, alarmppm, alarmperiod):   # draw graph and co values
        if alarmlevel == 0:
            centered_text(0, "CO Warner: No CO alarm", self.fonts[self.LARGE])
        else:
            if alarmperiod > 60:
                alarmstr = "CO: {:d} ppm longer {:d} min".format(alarmppm, math.floor(alarmperiod/60))
            else:
                alarmstr = "CO: {:d} ppm longer {:d} sec".format(alarmppm, math.floor(alarmperiod))
            centered_text(0, alarmstr, self.fonts[self.LARGE])
        self.graph(0, 40, 300, 200, co_values, 0, 120, 50, 100, timeout, self.TEXT_COLOR, self.TEXT_COLOR,
                   self.TEXT_COLOR, self.BG_COLOR, 3, 3, 5, 3)
        draw.text((320, 50 +  self.SMALL -  self.VERYSMALL), "Warnlevel:", font=verysmallfont, fill=self.TEXT_COLOR)
        right_text(50, "{:3d}".format(alarmlevel), self.fonts[self.SMALL])

        if len(co_values) > 0:
            draw.text((320, 120+SMALL-VERYSMALL), "CO act:", font=verysmallfont, fill=self.TEXT_COLOR)
            right_text(120, "{:3d}".format(co_values[len(co_values) - 1]), self.fonts[self.SMALL])
        draw.text((320, 140+SMALL-VERYSMALL), "CO max:", font=verysmallfont, fill=self.TEXT_COLOR)
        right_text(140, "{:3d}".format(co_max), self.fonts[self.SMALL])
        draw.text((320, 196), "R0:", font=verysmallfont, fill=self.TEXT_COLOR)
        right_text(196, "{:.1f}k".format(r0/1000), self.fonts[self.SMALL])

        bottom_line("Calibrate", "Mode", "Reset")

    def distance(self,now, gps_valid, gps_quality, gps_h_accuracy, distance_valid, gps_distance, gps_speed, baro_valid,
                 own_altitude, alt_diff, alt_diff_takeoff, vert_speed, ahrs_valid, ahrs_pitch, ahrs_roll,
                 ground_distance_valid, grounddistance, error_message):
        offset = 5
        self.centered_text(0, "GPS Distance", self.fonts[self.SMALL])
        lines = (
            ("Date", "{:0>2d}.{:0>2d}.{:0>4d}".format(now.day, now.month, now.year)),
            ("UTC", "{:0>2d}:{:0>2d}:{:0>2d},{:1d}".format(now.hour, now.minute, now.second,
                                                           math.floor(now.microsecond/100000)))
        )
        starty = self.dashboard(offset, self.SMALL, self.zerox-offset, lines, headline="Date/Time", rounding=True)
        t = "GPS-NoFix"
        accuracy = ""
        if gps_quality == 1:
            t = "3D GPS"
            accuracy = str(round(gps_h_accuracy, 1)) + "m"
        elif gps_quality == 2:
            t = "DGNSS"
            accuracy = str(round(gps_h_accuracy, 1)) + "m"
        gps_dist_str = "---"
        gps_speed_str = "---"
        if distance_valid:
            gps_dist_str = "{:4.0f}".format(gps_distance)
        if gps_valid:
            gps_speed_str = "{:3.1f}".format(gps_speed)
        lines = (
            ("GPS-Distance [m]", gps_dist_str),
            ("GPS-Speed [kts]", gps_speed_str),
            (t, accuracy)
        )
        starty = self.dashboard(offset, starty, self.zerox-offset, lines, headline="GPS", rounding=True)
        if ground_distance_valid:
            lines = (
                ("Grd Dist [cm]", "{:+3.1f}".format(grounddistance/10)),
            )
            self.dashboard(offset, starty, self.zerox-offset, lines, headline="Ground Sensor", rounding=True)

        starty = self.SMALL   # right column
        if ahrs_valid:
            lines = (
                ("Pitch [deg]", "{:+2d}".format(ahrs_pitch)),
                ("Roll [deg]", "{:+2d}".format(ahrs_roll)),
            )
            starty = self.dashboard(self.zerox+offset, starty, self.zerox-2*offset, lines, headline="AHRS", rounding=True)
        if baro_valid:
            if alt_diff_takeoff is not None:
                takeoff_str = "{:+5.1f}".format(alt_diff_takeoff)
            else:
                takeoff_str = "---"
            if alt_diff is not None:
                alt_diff_str = "{:+5.1f}".format(alt_diff)
            else:
                alt_diff_str = "---"
            lines = (
                ("Baro-Altitude [ft]", "{:5.0f}".format(own_altitude)),
                ("Vert Speed [ft]", "{:+4.0f}".format(vert_speed)),
                ("Ba-Diff r-up [ft]", alt_diff_str),
                ("Ba-Diff tof [ft]", takeoff_str),
            )
            self.dashboard(self.zerox+offset, starty, self.zerox-2*offset, lines, headline="Baro", rounding=True)

        if error_message is not None:
            self.centered_text(self.sizey//4, error_message, self.verylargefont)
        self.bottom_line("Stats/Set", "Mode", "Start")


    def distance_statistics(values, gps_valid, gps_altitude, dest_altitude, dest_alt_valid, ground_warnings):
        centered_text(0, "Start-/Landing Statistics", self.fonts[self.SMALL])

        st = '---'
        if 'start_time' in values:
            st = "{:0>2d}:{:0>2d}:{:0>2d},{:1d}".format(values['start_time'].hour, values['start_time'].minute,
                                                        values['start_time'].second,
                                                        math.floor(values['start_time'].microsecond / 100000))
        lines = (
            ("t-off time", st),
            ("t-off alt [ft]", form_line(values, 'start_altitude', "{:5.1f}")),
            ("t-off dist [m]", form_line(values, 'takeoff_distance', "{:3.1f}")),
            ("obst dist [m]", form_line(values, 'obstacle_distance_start', "{:3.1f}")),
        )
        starty = dashboard(5, 35, 225, True, "Takeoff", lines)

        lt = '---'
        if 'landing_time' in values:
            lt = "{:0>2d}:{:0>2d}:{:0>2d},{:1d}".format(values['landing_time'].hour, values['landing_time'].minute,
                                                        values['landing_time'].second,
                                                        math.floor(values['landing_time'].microsecond / 100000))
        lines = (
            ("ldg time", lt),
            ("ldg alt [ft]", form_line(values, 'landing_altitude', "{:5.1f}")),
            ("ldg dist [m]", form_line(values, 'landing_distance', "{:3.1f}")),
            ("obst dist [m]", form_line(values, 'obstacle_distance_landing', "{:3.1f}")),
        )
        starty = dashboard(250, 35, 225, True, "Landing", lines)
        if ground_warnings:
            if dest_alt_valid:
                dest_alt_str = "{:+5.0f}".format(dest_altitude)
            else:
                dest_alt_str = "---"
            if gps_valid:
                gps_alt_str = "{:+5.0f}".format(gps_altitude)
            else:
                gps_alt_str = "---"

            lines = (
                ("Act GPS-Alt [ft]", gps_alt_str),
                ("Destination Alt [ft]", dest_alt_str),
            )
            dashboard(5, starty + 10, 475, True, "Destination Elevation", lines)
        if not ground_warnings:
            bottom_line("", "Back", "")
        else:
            bottom_line("+100/-100ft", "Back", "+10/-10ft")


    def checklist_topic(ypos, topic, highlighted=False, toprint=True):
        xpos = 10
        xpos_remark = 50
        xpos_sub = 50
        topic_offset = 8
        subtopic_offset = 6
        remark_offset = 4
        topic_right_offset = 6

        y = ypos
        if 'TASK' in topic and topic['TASK'] is not None:
            if toprint:
                draw.text((xpos, ypos), topic['TASK'], font=smallfont, fill=self.TEXT_COLOR)    # Topic
        if 'CHECK' in topic and topic['CHECK'] is not None:
            if toprint:
                right_text(ypos, topic['CHECK'], font=smallfont, offset=topic_right_offset)     # Check
        y +=  self.SMALL
        if 'REMARK' in topic and topic['REMARK'] is not None:   # remark
            y += remark_offset
            if toprint:
                draw.text((xpos_remark, y), topic['REMARK'], font=verysmallfont, fill= self.TEXT_COLOR)  # remark
            y +=  self.VERYSMALL
        if 'TASK1' in topic and topic['TASK1'] is not None:    # subtopic
            y += subtopic_offset
            if toprint:
                draw.text((xpos_sub, y), topic['TASK1'], font=smallfont, fill= self.TEXT_COLOR)  # subtopic
            if 'CHECK1' in topic and topic['CHECK1'] is not None:
                if toprint:
                    right_text(y, topic['CHECK1'], font=smallfont, fill= self.TEXT_COLOR, offset=topic_right_offset)
            y +=  self.SMALL
        if 'TASK2' in topic and topic['TASK2'] is not None:   # subtopic2
            y += subtopic_offset
            if toprint:
                draw.text((xpos_sub, y), topic['TASK2'], font=smallfont, fill= self.TEXT_COLOR)  # subtopic
            if 'CHECK2' in topic and topic['CHECK2'] is not None:
                if toprint:
                    right_text(y, topic['CHECK2'], font=smallfont, fill= self.TEXT_COLOR, offset=topic_right_offset)
            y +=  self.SMALL
        if 'TASK3' in topic and topic['TASK3'] is not None:   # subtopic3
            y += subtopic_offset
            if toprint:
                draw.text((xpos_sub, y), topic['TASK3'], font=smallfont, fill="black")  # subtopic
            if 'CHECK3' in topic and topic['CHECK3'] is not None:
                if toprint:
                    right_text(y, topic['CHECK3'], font=smallfont, offset=topic_right_offset)
            y +=  self.SMALL
        if highlighted:   # draw frame around whole topic
            if toprint:
                draw.rounded_rectangle([3, ypos-4, sizex-2, y+6], width=3, radius=5, outline="black")
        return y + topic_offset


    def checklist(checklist_name, checklist_items, current_index, last_list):
        checklist_y = {'from': self.LARGE + 8, 'to': self.sizey -  self.SMALL - 6}
        global top_index

        centered_text(0, checklist_name, self.fonts[self.LARGE])
        if current_index == 0:
            top_index = 0     # new list, reset top index
        if current_index < top_index:
            top_index = current_index    # scroll up
        while True:  # check what would fit on the screen
            last_item = top_index
            size = checklist_topic(checklist_y['from'], checklist_items[last_item], highlighted=False, toprint=False)
            while True:
                if last_item + 1 < len(checklist_items):
                    last_item += 1
                else:
                    break    # everything fits to the end of the list
                size = checklist_topic(size, checklist_items[last_item], highlighted=False, toprint=False)
                if size > checklist_y['to']:   # last item did not fit
                    last_item -= 1
                    break
            # last item now shows the last one that fits
            if current_index + 1 <= last_item or last_item + 1 == len(checklist_items):
                # next item would also fit on screen or list is fully displayed
                break
            else:      # next item would not fit
                top_index += 1  # need to scroll, but now test again what would fit
                if current_index == len(checklist_items) - 1:  # list is finished
                    break
        # now display everything
        y = checklist_y['from']
        for item in range(top_index, last_item + 1):
            if item < len(checklist_items):
                y = checklist_topic(y, checklist_items[item], highlighted=(item == current_index), toprint=True)
        if current_index == 0:  # first item
            left = "PrevList"
        else:
            left = "Prev"
        if last_list and current_index == len(checklist_items) - 1:  # last_item
            bottom_line("Prev", "Mode", "")
        elif last_list:
            bottom_line(left, "Mode", "Checked")
        else:
            bottom_line(left, "NextList/Mode", "Checked")


# instantiate a single object in the file, needs to be done and inherited in every display module
radar_display = Epaper3in7()