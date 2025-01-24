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
    AIRCRAFT_COLOR = "black"
    MINIMAL_CIRCLE = 20  # minimal size of mode-s circle
    ARCPOSITION_EXCLUDE_FROM = 110
    ARCPOSITION_EXCLUDE_TO = 250
    PITCH_SCALE = 4.0
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
        self.ah_zeroy = self.sizey / 2  # zero line for ahrs
        self.ah_zerox = self.sizex / 2
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
        self.device.async_display_1Gray(self.device.getbuffer_optimized(epaper_image))

    def is_busy(self):
        return self.device.async_is_busy()

    def next_arcposition(old_arcposition):
        return GenericDisplay().next_arcposition(old_arcposition,
            exclude_from = ARCPOSITION_EXCLUDE_FROM, exclude_to= ARCPOSITION_EXCLUDE_TO)

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
        self.draw.bitmap((self.zerox-192/2, 0), logo, fill="black")
        versionstr = "Radar " + version
        self.centered_text(188, versionstr, self.largefont, fill="black")
        self.centered_text(sizey - 2 * VERYSMALL - 2, "Connecting to " + target_ip, self.verysmallfont, fill="black")
        self.display()
        time.sleep(seconds)


    def situation(self, connected, gpsconnected, ownalt, course, range, altdifference, bt_devices, sound_active,
                  gps_quality, gps_h_accuracy, optical_bar, basemode, extsound, co_alarmlevel, co_alarmstring):
        self.draw.ellipse((self.zerox-self.max_pixel/2, self.zeroy-self.max_pixel/2,
                           self.zerox+self.max_pixel/2, self.zeroy+self.max_pixel/2), outline="black")
        self.draw.ellipse((self.zerox-self.max_pixel/4, self.zeroy-self.max_pixel/4,
                           self.zerox+max_pixel/4, self.zeroy+max_pixel/4), outline="black")
        self.draw.ellipse((self.zerox-2, self.zeroy-2, self.zerox+2, self.zeroy+2), outline="black")
        self.draw.text((5, 1), str(range)+" nm", font=smallfont, fill="black")
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
        self.draw.text((5, self.SMALL+10), t, font=self.verysmallfont, fill="black")

        t = "FL"+str(round(ownalt / 100))
        textlength = self.draw.textlength(t, self.smallfont)
        self.draw.text((self.sizex - textlength - 5, self.SMALL+10), t, font=self.verysmallfont, fill="black")

        t = str(altdifference) + " ft"
        textlength = self.draw.textlength(t, self.smallfont)
        self.draw.text((self.sizex - textlength - 5, 1), t, font=self.smallfont, fill="black", align="right")

        text = str(course) + '°'
        self.centered_text(1, text, self.smallfont, fill="black")

        if not gpsconnected:
            self.centered_text(70, "No GPS", self.smallfont, fill="black")
        if not connected:
            self.centered_text(30, "No Connection!", self.smallfont, fill="black")
        if co_alarmlevel > 0:
            self.tered_text(250, "CO Alarm: " + co_alarmstring, self.smallfont, fill="black")

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
                           font=self.awesomefont, fill="black")

        # optical keep alive bar at right side
        self.draw.line((self.sizex-8, 80+optical_bar*10, self.sizex-8, 80+optical_bar*10+8), fill="black", width=5)


    def timer(utctime, stoptime, laptime, laptime_head, left_text, middle_text, right_t, timer_runs):
        draw.text((5, 0), "UTC", font=smallfont, fill="black")
        centered_text(SMALL, utctime, self.verylargefont, fill="black")
        if stoptime is not None:
            draw.text((5, SMALL+VERYLARGE), "Timer", font=smallfont, fill="black")
            centered_text(2*SMALL+VERYLARGE, stoptime, self.verylargefont, fill="black")
            if laptime is not None:
                draw.text((5, 2*SMALL + 2 * VERYLARGE), laptime_head, font=smallfont, fill="black")
                centered_text(3*SMALL+2*VERYLARGE, laptime, self.verylargefont, fill="black")

        draw.text((5, sizey-SMALL-3), left_text, font=smallfont, fill="black")
        textlength = draw.textlength(right_t, self.smallfont)
        draw.text((sizex-textlength-8, sizey-SMALL-3), right_t, font=smallfont, fill="black", align="right")
        centered_text(sizey-SMALL-3, middle_text, self.smallfont, fill="black")


    def meter(current, start_value, end_value, from_degree, to_degree, size, center_x, center_y,
              marks_distance, small_marks_distance, middle_text1, middle_text2):
        big_mark_length = 20
        small_mark_length = 10
        text_distance = 10
        arrow_line_size = 12  # must be an even number
        arrow = ((arrow_line_size / 2, 0), (-arrow_line_size / 2, 0), (-arrow_line_size / 2, -size / 2 + 50),
                 (0, -size / 2 + 10), (arrow_line_size / 2, -size / 2 + 50), (arrow_line_size / 2, 0))
        # points of arrow at angle 0 (pointing up) for line drawing

        deg_per_value = (to_degree - from_degree) / (end_value - start_value)

        draw.arc((center_x-size/2, center_y-size/2, center_x+size/2, center_y+size/2),
                 from_degree-90, to_degree-90, width=6, fill="black")
        # small marks first
        line = ((0, -size/2+1), (0, -size/2+small_mark_length))
        m = start_value
        while m <= end_value:
            angle = deg_per_value * (m-start_value) + from_degree
            mark = translate(angle, line, (center_x, center_y))
            draw.line(mark, fill="black", width=2)
            m += small_marks_distance
        # self.LARG marks
        line = ((0, -size/2+1), (0, -size/2+big_mark_length))
        m = start_value
        while m <= end_value:
            angle = deg_per_value*(m-start_value) + from_degree
            mark = translate(angle, line, (center_x, center_y))
            draw.line(mark, fill="black", width=4)
            # text
            marktext = str(m)
            tl = draw.textlength(marktext, self.largefont)
            t_center = translate(angle, ((0, -size/2 + big_mark_length + self.LARG/2 + text_distance), ), (center_x, center_y))
            draw.text((t_center[0][0]-tl/2, t_center[0][1]-LARGE/2), marktext, fill="black", font=largefont)
            m += marks_distance
        # arrow
        if current > end_value:   # normalize values in allowed ranges
            current = end_value
        elif current < start_value:
            current = start_value
        angle = deg_per_value * (current - start_value) + from_degree
        ar = translate(angle, arrow, (center_x, center_y))
        draw.line(ar, fill="black", width=4)
        # centerpoint
        draw.ellipse((center_x - 10, center_y - 10, center_x + 10, center_y + 10), fill="black")

        if middle_text1 is not None:
            tl = draw.textlength(middle_text1, self.smallfont)
            draw.text((center_x - tl/2, center_y - SMALL - 20), middle_text1, font=smallfont, fill="black", align="left")
        if middle_text2 is not None:
            tl = draw.textlength(middle_text2, self.smallfont)
            draw.text((center_x-tl/2, center_y+20), middle_text2, font=smallfont, fill="black", align="left")


    def gmeter(current, maxg, ming, error_message):
        gm_size = 280
        meter(current, -3, 5, 110, 430, gm_size, 140, 140, 1, 0.25, "G-Force", None)

        right_center_x = (sizex-gm_size)/2+gm_size    # center of remaining part
        t = "G-Meter"
        tl = draw.textlength(t, self.largefont)
        draw.text((right_center_x - tl / 2, 30), t, font=largefont, fill="black", align="left")
        draw.text((gm_size+30, 98), "max", font=smallfont, fill="black")
        right_text(95, "{:+1.2f}".format(maxg), self.largefont, fill="black")
        if error_message is None:
            draw.text((gm_size+30, 138), "act", font=smallfont, fill="black")
            right_text(135, "{:+1.2f}".format(current), self.largefont, fill="black")
        else:
            draw.text((gm_size+30, 138), error_message, font=largefont, fill="black")
        draw.text((gm_size+30, 178), "min", font=smallfont, fill="black")
        right_text(175, "{:+1.2f}".format(ming), self.largefont, fill="black")

        bottom_line("", "    Mode", "Reset")


    def compass(heading, error_message):
        czerox = self.sizex / 2
        czeroy = self.sizey / 2
        csize = int(self.sizey / 2) # radius of compass rose

        draw.ellipse((self.sizex/2-csize, 0, self.sizex/2+csize-1, self.sizey - 1), outline="black", fill="white", width=4)
        draw.bitmap((self.zerox - 60, 70), compass_aircraft, fill="black")
        draw.line((czerox, 20, czerox, 70), fill="black", width=4)
        text = str(heading) + '°'
        tl = draw.textlength(text, self.smallfont)
        draw.text((self.sizex - tl - 100, self.sizey - SMALL - 10), text, font=smallfont, fill="black", align="right")
        for m in range(0, 360, 10):
            s = math.sin(math.radians(m - heading + 90))
            c = math.cos(math.radians(m - heading + 90))
            if m % 30 != 0:
                draw.line((czerox - (csize - 1) * c, czeroy - (csize - 1) * s, czerox - (csize - CM_SIZE) * c,
                           czeroy - (csize - CM_SIZE) * s), fill="black", width=2)
            else:
                draw.line((czerox - (csize - 1) * c, czeroy - (csize - 1) * s, czerox - (csize - CM_SIZE) * c,
                           czeroy - (csize - CM_SIZE) * s), fill="black", width=4)
                cdraw.rectangle((0, 0, self.LARG * 2, self.LARGE * 2), fill="black")
                if m == 0:
                    mark = "N"
                elif m == 90:
                    mark = "E"
                elif m == 180:
                    mark = "S"
                elif m == 270:
                    mark = "W"
                else:
                    mark = str(int(m / 10))
                if m % 90 != 0:
                    tl = draw.textlength(mark, self.largefont)
                    cdraw.text(((self.LARGE * 2 - tl) / 2, self.LARGE / 2), mark, 1, font=largefont)
                else:
                    tl = draw.textlength(mark, self.morelargefont)
                    cdraw.text(((self.LARGE * 2 - tl) / 2, (self.LARGE * 2 - self.MORELARGE) / 2), mark, 1, font=morelargefont)
                rotmask = self.mask.rotate(-m + heading, expand=False)
                center = (czerox - (csize - CM_SIZE - self.LARGE / 2) * c, czeroy - (csize - CM_SIZE - self.LARGE / 2) * s)
                epaper_image.paste("black", (round(center[0] - self.LARGE), round(center[1] - self.LARGE)), rotmask)
        if error_message is not None:
            self.centered_text(120, error_message, self.largefont, fill="black")


    def vsi(vertical_speed, flight_level, gps_speed, gps_course, gps_altitude, vertical_max, vertical_min,
            error_message):
        meter(vertical_speed/100, -20, 20, 110, 430, sizey, sizey/2, sizey/2, 5, 1, None, None)
        draw.text((35, sizey/2 - VERYSMALL - 25), "up", font=verysmallfont, fill="black", align="left")
        draw.text((35, sizey/2 + 25), "dn", font=verysmallfont, fill="black", align="left")
        middle_text = "Vertical Speed"
        tl = draw.textlength(middle_text, self.smallfont)
        draw.text((sizey/2 - tl / 2, sizey/2 - VERYSMALL - 10), middle_text, font=verysmallfont, fill="black", align="left")
        middle_text = "100 feet per min"
        tl = draw.textlength(middle_text, self.smallfont)
        draw.text((sizey/2 - tl / 2, sizey/2 + 10), middle_text, font=verysmallfont, fill="black", align="left")

        # right data display
        draw.text((300, 10), "Vert Speed [ft/min]", font=verysmallfont, fill="black", align="left")
        draw.text((330, 31), "act", font=verysmallfont, fill="black", align="left")
        draw.text((330, 55), "max", font=verysmallfont, fill="black", align="left")
        draw.text((330, 79), "min", font=verysmallfont, fill="black", align="left")
        right_text(28, "{:+1.0f}".format(vertical_speed), self.smallfont, fill="black")
        right_text(52, "{:+1.0f}".format(vertical_max), self.smallfont, fill="black")
        right_text(76, "{:+1.0f}".format(vertical_min), self.smallfont, fill="black")
        draw.text((300, 163), "Flight-Level", font=verysmallfont, fill="black", align="left")
        right_text(160, "{:1.0f}".format(round(flight_level/100)), self.smallfont, fill="black")
        draw.text((300, 187), "GPS-Alt [ft]", font=verysmallfont, fill="black", align="left")
        right_text(184, "{:1.0f}".format(gps_altitude), self.smallfont, fill="black")
        draw.text((300, 211), "GpsSpd [kts]", font=verysmallfont, fill="black", align="left")
        right_text(208, "{:1.1f}".format(gps_speed), self.smallfont, fill="black")

        if error_message is not None:
            centered_text(60, error_message, self.verylargefont, fill="black")

        bottom_line("", "    Mode", "Reset")


    def shutdown(countdown, shutdownmode):
        if shutdownmode == 0:   # shutdown stratux + display
            message = "Shutdown stratux & display"
        elif shutdownmode == 1:
            message = "Shutdown display"
        else:
            message = "Reboot"
        centered_text(10, message, self.largefont, fill="black")
        message = "in " + str(countdown) + " seconds!"
        centered_text(40, message, self.largefont, fill="black")
        message = "Press left button to cancel ..."
        centered_text(110, message, self.smallfont, fill="black")
        message = "Press middle for display only ..."
        centered_text(140, message, self.smallfont, fill="black")
        message = "Press right for reboot all ..."
        centered_text(170, message, self.smallfont, fill="black")

        bottom_line("Cancel", "Display only", "Reboot")


    def rollmarks(roll):
        if ah_zerox > ah_zeroy:
            di = ah_zeroy
        else:
            di = ah_zerox

        for rm in ROLL_POSMARKS:
            s = math.sin(math.radians(rm - roll + 90))
            c = math.cos(math.radians(rm - roll + 90))
            if rm % 30 == 0:
                draw.line((ah_zerox - di * c, ah_zeroy - di * s, ah_zerox - (di - 24) * c,
                           ah_zeroy - (di - 24) * s), fill="black", width=4)
            else:
                draw.line((ah_zerox - di * c, ah_zeroy - di * s, ah_zerox - (di - 16) * c,
                           ah_zeroy - (di - 16) * s), fill="black", width=4)
        draw.polygon((ah_zerox, 24, ah_zerox - 16, 24 + 12, ah_zerox + 16, 24 + 12), fill="black")


    def linepoints(pitch, roll, pitch_distance, length):
        s = math.sin(math.radians(180 + roll))
        c = math.cos(math.radians(180 + roll))
        dist = (-pitch + pitch_distance) * PITCH_SCALE
        move = (dist * s, dist * c)
        s1 = math.sin(math.radians(-90 - roll))
        c1 = math.cos(math.radians(-90 - roll))
        p1 = (ah_zerox - length * s1, ah_zeroy + length * c1)
        p2 = (ah_zerox + length * s1, ah_zeroy - length * c1)
        ps = (p1[0] + move[0], p1[1] + move[1])
        pe = (p2[0] + move[0], p2[1] + move[1])
        return ps, pe


    def slip(slipskid):
        slipsize = 12
        slipscale = 15
        if slipskid < -10:
            slipskid = -10
        elif slipskid > 10:
            slipskid = 10

        draw.rectangle((ah_zerox - 150, sizey - slipsize * 2, ah_zerox + 150, sizey - 1),
                       fill="black")
        draw.ellipse((ah_zerox - slipskid * slipscale - slipsize, sizey - slipsize * 2,
                      ah_zerox - slipskid * slipscale + slipsize, sizey - 1), fill="white")
        draw.line((ah_zerox, sizey - slipsize * 2, ah_zerox, sizey - 1), fill="black", width=6)
        draw.line((ah_zerox, sizey - slipsize * 2, ah_zerox, sizey - 1), fill="white", width=2)


    def ahrs(pitch, roll, heading, slipskid, error_message):
        # print("AHRS: pitch ", pitch, " roll ", roll, " heading ", heading, " slipskid ", slipskid)
        h1, h2 = linepoints(pitch, roll, 0, 600)  # horizon points
        h3, h4 = linepoints(pitch, roll, -180, 600)
        draw.polygon((h1, h2, h4, h3), fill="white")  # earth
        h3, h4 = linepoints(pitch, roll, 180, 600)
        draw.polygon((h1, h2, h4, h3), fill="white")  # sky
        draw.line((h1, h2), fill="black", width=4)  # horizon line

        earthfill = 0
        while earthfill > -180:
            earthfill -= 3
            draw.line((linepoints(pitch, roll, earthfill, 600)), fill="black", width=1)

        for pm in PITCH_POSMARKS:  # pitchmarks
            draw.line((linepoints(pitch, roll, pm, 30)), fill="black", width=4)

        # pointer in the middle
        draw.line((ah_zerox - 90, ah_zeroy, ah_zerox - 30, ah_zeroy), width=6, fill="black")
        draw.line((ah_zerox + 90, ah_zeroy, ah_zerox + 30, ah_zeroy), width=6, fill="black")
        draw.polygon((ah_zerox, ah_zeroy + 4, ah_zerox - 20, ah_zeroy + 16, ah_zerox + 20, ah_zeroy + 16),
                     fill="black")

        # roll indicator
        rollmarks(roll)
        # slip indicator
        slip(slipskid)

        # infotext = "P:" + str(pitch) + " R:" + str(roll)
        if error_message:
            centered_text(80, error_message, self.smallfont, fill="black")
        bottom_line("Levl", "", "Zero")


    def text_screen(headline, subline, text, left_text, middle_text, r_text):
        centered_text(0, headline, self.verylargefont, fill="black")
        txt_starty = VERYLARGE
        if subline is not None:
            centered_text(txt_starty, subline, self.largefont, fill="black")
            txt_starty += self.LARGE
        draw.text((5, txt_starty), text, font=smallfont, fill="black")
        bottom_line(left_text, middle_text, r_text)


    def screen_input(headline, subline, text, left, middle, right, prefix, inp, suffix):
        centered_text(0, headline, self.largefont, fill="black")
        txt_starty = self.LARGE
        if subline is not None:
            centered_text(LARGE, subline, self.smallfont, fill="black")
            txt_starty += self.LARGE
        bbox = draw.textbbox((0, txt_starty), text, font=smallfont)
        draw.text((0, txt_starty), text, font=smallfont, fill="black")
        bbox_p = draw.textbbox((bbox[0], bbox[3]), prefix, font=smallfont)
        draw.text((bbox[0], bbox[3]), prefix, fill="black", font=smallfont)
        bbox_rect = draw.textbbox((bbox_p[2], bbox[3]), inp, font=smallfont)
        draw.rectangle(bbox_rect, fill="black")
        draw.text((bbox_rect[0], bbox[3]), inp, font=smallfont, fill="white")
        draw.text((bbox_rect[2], bbox[3]), suffix, font=smallfont, fill="black")

        bottom_line(left, middle, right)


    def bar(y, text, val, max_val, yellow, red, unit="", valtext=None, minval=0):
        bar_start = 100
        bar_end = 420

        draw.text((5, y), text, font=verysmallfont, fill="black", align="left")
        right_val = str(int(max_val)) + unit
        textlength = draw.textlength(right_val, self.smallfont)
        draw.text((sizex - textlength - 5, y), right_val, font=verysmallfont, fill="black", align="right")
        draw.rounded_rectangle([bar_start-2, y-2, bar_end+2, y+VERYSMALL+2], radius=3, fill=None, outline="black", width=1)
        color = "black"
        if val < minval:
            val = minval   # to display a minimum bar, valtext should be provided in this case
        if max_val != 0:
            xval = bar_start + (bar_end - bar_start) * val / max_val
        else:
            xval = bar_start
        for b in range(int(bar_start), int(xval), 5):
            draw.line([(b, y), (b, y+VERYSMALL)], fill="black", width=1)
        # draw.rectangle([bar_start, y, xval, y+VERYSMALL], fill=color, outline=None)
        if valtext is not None:
            t = valtext
        else:
            t = str(val)
        tl = draw.textlength(t, self.smallfont)
        draw.text(((bar_end-bar_start)/2+bar_start-tl/2, y), t, font=verysmallfont, fill="black",
                  stroke_width=1, stroke_fill="white")
        return y+VERYSMALL+12


    def round_text(x, y, text, color, yesno=True, out=None):
        tl = draw.textlength(text, self.smallfont)
        draw.rounded_rectangle([x, y, x+tl+10, y+VERYSMALL+2], radius=4, fill=color, outline=out)
        draw.text((x+5, y), text, font=verysmallfont, fill="black")
        if not yesno:
            draw.line([x, y+VERYSMALL+2, x+tl+10, y], fill="black", width=2)
        return x+tl+20


    def stratux(stat, altitude, gps_alt, gps_quality):
        starty = 0
        centered_text(0, "Stratux " + stat['version'], self.smallfont, fill="black")
        starty += SMALL+8
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
        draw.text((5, starty), "GPS hw", font=verysmallfont, fill="black")
        draw.text((100, starty), stat['GPS_detected_type'], font=verysmallfont, fill="black")
        starty += VERYSMALL + 5
        draw.text((5, starty), "GPS sol", font=verysmallfont, fill="black")
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
        draw.text((100, starty), t + gps, font=verysmallfont, fill="black")

        t = "Sat: " + str(stat['GPS_satellites_locked']) + " sol/" + \
            str(stat['GPS_satellites_seen']) + " seen/" + str(stat['GPS_satellites_tracked']) + " track"
        draw.text((220, starty), t, font=verysmallfont, fill="black")

        starty += VERYSMALL+5

        draw.text((5, starty), "altitudes", font=verysmallfont, fill="black")
        if stat['GPS_position_accuracy'] < 19999:
            alt = '{:5.0f}'.format(gps_alt)
        else:
            alt = " ---"
        t = "P-Alt {0} ft".format(round(altitude))
        draw.text((100, starty), t, font=verysmallfont, fill="black")
        t = "Corr {0:+} ft".format(stat['AltitudeOffset'])
        draw.text((220, starty), t, font=verysmallfont, fill="black")
        t = "GPS-Alt " + alt + " ft"
        draw.text((340, starty), t, font=verysmallfont, fill="black")
        starty += VERYSMALL + 5
        draw.text((5, starty), "sensors", font=verysmallfont, fill="black")
        x = round_text(100, starty, "IMU", "white", stat['IMUConnected'], out="black")
        round_text(x, starty, "BMP", "white", stat['BMPConnected'], out="black")
        bottom_line("+10 ft", "Mode", "-10 ft")


    def flighttime(last_flights):
        starty = 0
        centered_text(0, "Flight Logs ", self.smallfont, fill="black")
        starty += SMALL + 10
        draw.text((20, starty), "Date", font=verysmallfont, fill="black")
        draw.text((120, starty), "Start", font=verysmallfont, fill="black")
        draw.text((220, starty), "Duration", font=verysmallfont, fill="black")
        draw.text((350, starty), "Ldg", font=verysmallfont, fill="black")
        starty += VERYSMALL + 10

        maxlines = 8
        for f in last_flights:
            f[0] = f[0].replace(second=0, microsecond=0)  # round down start time to minutes
            draw.text((20, starty), f[0].strftime("%d.%m.%y"), font=verysmallfont, fill="black")
            draw.text((120, starty), f[0].strftime("%H:%M"), font=verysmallfont, fill="black")
            if f[1] != 0:    # ==0 means still in the air
                f[1] = f[1].replace(second=0, microsecond=0)   # round down
                delta = (f[1]-f[0]).total_seconds()
                draw.text((350, starty), f[1].strftime("%H:%M"), font=verysmallfont, fill="black")
            else:
                delta = (datetime.datetime.now(datetime.timezone.utc).replace(second=0, microsecond=0)
                         - f[0]).total_seconds()
                draw.text((350, starty), "in the air", font=verysmallfont, fill="black")
            hours, remainder = divmod(delta, 3600)
            minutes, seconds = divmod(remainder, 60)
            out = '  {:02}:{:02}  '.format(int(hours), int(minutes))
            round_text(220, starty, out, "white", out="black")
            starty += VERYSMALL + 5
            maxlines -= 1
            if maxlines <= 0:
                break
        bottom_line("", "Mode", "Clear")


    def cowarner(co_values, co_max, r0, timeout, alarmlevel, alarmppm, alarmperiod):   # draw graph and co values
        if alarmlevel == 0:
            centered_text(0, "CO Warner: No CO alarm", self.largefont, fill="black")
        else:
            if alarmperiod > 60:
                alarmstr = "CO: {:d} ppm longer {:d} min".format(alarmppm, math.floor(alarmperiod/60))
            else:
                alarmstr = "CO: {:d} ppm longer {:d} sec".format(alarmppm, math.floor(alarmperiod))
            centered_text(0, alarmstr, self.largefont, fill="black")
        self.graph(0, 40, 300, 200, co_values, 0, 120, 50, 100, timeout, "black", "black", "black", "white", 3, 3, 5, 3)
        draw.text((320, 50 + SMALL - VERYSMALL), "Warnlevel:", font=verysmallfont, fill="black")
        right_text(50, "{:3d}".format(alarmlevel), self.smallfont, fill="black")

        if len(co_values) > 0:
            draw.text((320, 120+SMALL-VERYSMALL), "CO act:", font=verysmallfont, fill="black")
            right_text(120, "{:3d}".format(co_values[len(co_values) - 1]), self.smallfont, fill="black")
        draw.text((320, 140+SMALL-VERYSMALL), "CO max:", font=verysmallfont, fill="black")
        right_text(140, "{:3d}".format(co_max), self.smallfont, fill="black")
        draw.text((320, 196), "R0:", font=verysmallfont, fill="black")
        right_text(196, "{:.1f}k".format(r0/1000), self.smallfont, fill="black")

        bottom_line("Calibrate", "Mode", "Reset")


    def dashboard(x, y, dsizex, rounding, headline, lines):
        # dashboard, arguments are lines = ("text", "value"), ....
        starty = y + VERYSMALL/2
        for line in lines:
            draw.text((x + 7, starty + (SMALL - VERYSMALL) / 2), line[0], font=verysmallfont, fill="black", align="left")
            tl = draw.textlength(line[1], self.smallfont)
            draw.text((x + dsizex - 7 - tl, starty), line[1], font=smallfont, fill="black")
            starty += SMALL + 3
        if rounding:
            starty += VERYSMALL/2
            draw.rounded_rectangle([x, y, x + dsizex, starty], radius=6, fill=None, outline="black", width=2)
            tl = draw.textlength(headline, self.smallfont)
            draw.rectangle([x + 20, y - SMALL/2, x + 20 + tl + 8, y + SMALL/2], fill="white", outline=None)
        draw.text((x+20+4, y - VERYSMALL/2), headline, font=verysmallfont, fill="black")
        return starty


    def distance(now, gps_valid, gps_quality, gps_h_accuracy, distance_valid, gps_distance, gps_speed, baro_valid,
                 own_altitude, alt_diff, alt_diff_takeoff, vert_speed, ahrs_valid, ahrs_pitch, ahrs_roll,
                 ground_distance_valid, grounddistance, error_message):

        centered_text(0, "GPS Distance", self.smallfont, fill="black")

        lines = (
            ("Date", "{:0>2d}.{:0>2d}.{:0>4d}".format(now.day, now.month, now.year)),
            ("UTC", "{:0>2d}:{:0>2d}:{:0>2d},{:1d}".format(now.hour, now.minute, now.second,
                                                           math.floor(now.microsecond/100000)))
        )
        starty = dashboard(5, 35, 225, True, "Date/Time", lines)

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
        starty = dashboard(5, starty, 225, True, "GPS", lines)
        if ground_distance_valid:
            lines = (
                ("Grd Dist [cm]", "{:+3.1f}".format(grounddistance/10)),
            )
            dashboard(5, starty, 225, True, "Ground Sensor", lines)

        starty = 35   # right column
        if ahrs_valid:
            lines = (
                ("Pitch [deg]", "{:+2d}".format(ahrs_pitch)),
                ("Roll [deg]", "{:+2d}".format(ahrs_roll)),
            )
            starty = dashboard(250, 35, 225, True, "AHRS", lines)
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
            dashboard(250, starty, 225, True, "Baro", lines)

        if error_message is not None:
            centered_text(60, error_message, self.verylargefont, fill="black")
        bottom_line("Stats/Set", "Mode", "Start")


    def distance_statistics(values, gps_valid, gps_altitude, dest_altitude, dest_alt_valid, ground_warnings):
        centered_text(0, "Start-/Landing Statistics", self.smallfont, fill="black")

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
                draw.text((xpos, ypos), topic['TASK'], font=smallfont, fill="black")    # Topic
        if 'CHECK' in topic and topic['CHECK'] is not None:
            if toprint:
                right_text(ypos, topic['CHECK'], font=smallfont, fill="black", offset=topic_right_offset)     # Check
        y += SMALL
        if 'REMARK' in topic and topic['REMARK'] is not None:   # remark
            y += remark_offset
            if toprint:
                draw.text((xpos_remark, y), topic['REMARK'], font=verysmallfont, fill="black")  # remark
            y += VERYSMALL
        if 'TASK1' in topic and topic['TASK1'] is not None:    # subtopic
            y += subtopic_offset
            if toprint:
                draw.text((xpos_sub, y), topic['TASK1'], font=smallfont, fill="black")  # subtopic
            if 'CHECK1' in topic and topic['CHECK1'] is not None:
                if toprint:
                    right_text(y, topic['CHECK1'], font=smallfont, fill="black", offset=topic_right_offset)
            y += SMALL
        if 'TASK2' in topic and topic['TASK2'] is not None:   # subtopic2
            y += subtopic_offset
            if toprint:
                draw.text((xpos_sub, y), topic['TASK2'], font=smallfont, fill="black")  # subtopic
            if 'CHECK2' in topic and topic['CHECK2'] is not None:
                if toprint:
                    right_text(y, topic['CHECK2'], font=smallfont, fill="black", offset=topic_right_offset)
            y += SMALL
        if 'TASK3' in topic and topic['TASK3'] is not None:   # subtopic3
            y += subtopic_offset
            if toprint:
                draw.text((xpos_sub, y), topic['TASK3'], font=smallfont, fill="black")  # subtopic
            if 'CHECK3' in topic and topic['CHECK3'] is not None:
                if toprint:
                    right_text(y, topic['CHECK3'], font=smallfont, fill="black", offset=topic_right_offset)
            y += SMALL
        if highlighted:   # draw frame around whole topic
            if toprint:
                draw.rounded_rectangle([3, ypos-4, sizex-2, y+6], width=3, radius=5, outline="black")
        return y + topic_offset


    def checklist(checklist_name, checklist_items, current_index, last_list):
        checklist_y = {'from': self.LARGE + 8, 'to': sizey - SMALL - 6}
        global top_index

        centered_text(0, checklist_name, self.largefont, fill="black")
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