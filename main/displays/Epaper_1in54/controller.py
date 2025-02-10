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

from . import epd1in54_V2
from .. import dcommon
from PIL import Image, ImageDraw, ImageFont
import math
import time
import datetime
from pathlib import Path
import logging


class Epaper1in54(dcommon.GenericDisplay):
    VERYLARGE = 30  # timer
    MORELARGE = 26
    LARGE = 24  # size of height indications of aircraft
    SMALL = 20  # size of information indications on top and bottom
    VERYSMALL = 18
    AWESOME_FONTSIZE = 18  # bluetooth indicator
    AIRCRAFT_SIZE = 4  # size of aircraft arrow
    MINIMAL_CIRCLE = 10  # minimal size of mode-s circle
    ARCPOSITION_EXCLUDE_FROM = 0
    ARCPOSITION_EXCLUDE_TO = 0
    # colors
    BG_COLOR = "white"
    TEXT_COLOR = "black"
    AIRCRAFT_COLOR = "black"
    # AHRS
    AHRS_EARTH_COLOR = "white"  # how ahrs displays the earth
    AHRS_SKY_COLOR = "white"  # how ahrs displays the sky
    AHRS_HORIZON_COLOR = "black"  # how ahrs displays the horizon
    AHRS_MARKS_COLOR = "black"  # color of marks and corresponding text in ahrs
    CM_SIZE = 10  # size of markings in ahrs
    ANGLE_OFFSET = 270  # offset for calculating angles in displays

    def init(self, fullcircle=False):
        self.device = epd1in54_V2.EPD()
        self.device.init(0)
        self.device.Clear(0xFF)  # necessary to overwrite everything
        self.epaper_image = Image.new('1', (self.device.height, self.device.width), 0xFF)
        self.draw = ImageDraw.Draw(self.epaper_image)
        self.device.init(1)
        self.device.Clear(0xFF)
        self.sizex = self.device.height
        self.sizey = self.device.width
        self.zerox = self.sizex / 2
        self.zeroy = self.sizey / 2
        self.max_pixel = self.sizey
        self.ah_zeroy = self.sizey // 2  # zero line for ahrs
        self.ah_zerox = self.sizex // 2
        # measure time for refresh
        start = time.time()
        # do sync version of display to measure time
        self.device.displayPart_mod(self.device.getbuffer_optimized(self.epaper_image))
        end = time.time()
        self.display_refresh = end - start
        # compass preparation
        pic_path = str(Path(__file__).resolve().parent.joinpath('plane-white-96x96.bmp'))
        self.compass_aircraft = Image.open(pic_path)
        self.mask = Image.new('1', (self.LARGE * 2, self.LARGE * 2))
        self.cdraw = ImageDraw.Draw(self.mask)
        self.rlog.debug(
            f'Epaper_1in54 selected: sizex={self.sizex} sizey={self.sizey} zero=({self.zerox}, {self.zeroy}) '
            f'refresh-time: {str(round(self.display_refresh, 2))} secs')
        return self.max_pixel, self.zerox, self.zeroy, self.display_refresh

    def display(self):
        self.device.async_displayPart(self.device.getbuffer_optimized(self.epaper_image))

    def is_busy(self):
        return self.device.async_is_busy()

    @staticmethod
    def next_arcposition(old_arcposition):
        return dcommon.GenericDisplay().next_arcposition(old_arcposition,
            exclude_from=Epaper1in54().ARCPOSITION_EXCLUDE_FROM, exclude_to=Epaper1in54().ARCPOSITION_EXCLUDE_TO)

    def cleanup(self):
        self.device.init(0)
        self.device.Clear(0xFF)
        self.device.sleep_nowait()

    def refresh(self):
        self.device.Clear(0xFF)  # necessary to overwrite everything
        self.device.init(1)


    def startup(self, version, target_ip, seconds):
        logopath = str(Path(__file__).resolve().parent.joinpath('stratux-logo-150x150.bmp'))
        logo = Image.open(logopath)
        self.draw.bitmap((self.zerox-150//2, 0), logo, fill="black")
        versionstr = f"Radar {version}"
        self.centered_text(150, versionstr, self.VERYLARGE)
        self.display()
        time.sleep(seconds)

    def situation(self, connected, gpsconnected, ownalt, course, range, altdifference, bt_devices, sound_active,
                  gps_quality, gps_h_accuracy, optical_bar, basemode, extsound, co_alarmlevel, co_alarmstring):
        self.draw.ellipse((self.zerox - self.max_pixel // 2, self.zeroy - self.max_pixel // 2,
                           self.zerox + self.max_pixel // 2 - 1, self.zeroy + self.max_pixel // 2 - 1), outline=self.TEXT_COLOR)
        self.draw.ellipse((self.zerox - self.max_pixel // 4, self.zeroy - self.max_pixel // 4,
                           self.zerox + self.max_pixel // 4 - 1, self.zeroy + self.max_pixel // 4 - 1), outline=self.TEXT_COLOR)
        self.draw.ellipse((self.zerox - 2, self.zeroy - 2, self.zerox + 2, self.zeroy + 2), outline=self.TEXT_COLOR)
        self.draw.text((0, 0), f"{range}", font=self.fonts[self.SMALL], fill=self.TEXT_COLOR)
        self.draw.text((0, self.SMALL), "nm", font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)
        self.draw.text((0, self.sizey - self.SMALL), f"FL{round(ownalt / 100)}", font=self.fonts[self.SMALL], fill="black")

        t = f"{altdifference // 1000}k" if altdifference >= 10000 else f"{altdifference}"
        tl = self.draw.textlength(t, self.fonts[self.SMALL])
        self.draw.text((self.sizex - tl, 0), t, font=self.fonts[self.SMALL], fill=self.TEXT_COLOR, align="right")
        text = "ft"
        tl = self.draw.textlength(text, self.fonts[self.VERYSMALL])
        self.draw.text((self.sizex - tl, self.SMALL), text, font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR,
                       align="right")

        text = f"{course}°"
        tl = self.draw.textlength(text, self.fonts[self.SMALL])
        self.draw.text((self.sizex - tl, self.sizey - self.SMALL), text, font=self.fonts[self.SMALL], fill=self.TEXT_COLOR, align="right")

        if not gpsconnected:
            centered_text(15, "No GPS", self.SMALL)
        if not connected:
            centered_text(75, "No connection!", self.SMALL)
        if co_alarmlevel > 0:
            centered_text(self.sizey - 3 * self.SMALL, "CO Alarm!", self.SMALL)
            centered_text(self.sizey - 2 * self.SMALL, co_alarmstring, self.SMALL)

        if extsound or bt_devices > 0:
            t = "\uf028" * extsound + "\uf293" * (bt_devices > 0) if sound_active else "\uf1f6"
            tl = self.draw.textlength(t, self.AWESOME_FONTSIZE)
            self.draw.text((self.sizex - tl, self.sizey - 2 * self.SMALL), t, font=self.awesomefont,
                           fill=self.TEXT_COLOR)

        self.draw.line((2, 150 + (optical_bar % 5) * 5, 2, 150 + (optical_bar % 5) * 5 + 6),
                       fill=self.TEXT_COLOR, width=4)

    def gmeter(self, current, maxg, ming, error_message):
        gm_size = self.sizex
        self.meter(current, -3, 5, 120, 420, gm_size, self.zerox, self.zeroy, 1, 0.25, "G-Force", None)
        self.draw.text((self.zerox + 13, 80), "max", font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)
        self.right_text(80, f"{maxg:+1.2f}", self.SMALL)
        if error_message:
            self.centered_text(57, error_message, self.LARGE)
        self.draw.text((self.zerox + 13, 102), "min", font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)
        self.right_text(102, f"{ming:+1.2f}", self.SMALL)
        self.bottom_line("", "", "Rst")

    def vsi(self, vertical_speed, flight_level, gps_speed, gps_course, gps_altitude, vertical_max, vertical_min,
            error_message):
        self.meter(vertical_speed / 100, -20, 20, 110, 430, self.sizey, self.sizey // 2,
                   self.sizey // 2, 5, 1, "Vert Spd", "100 ftm/min",
                   middle_fontsize=self.VERYSMALL)
        self.draw.text((15, self.sizey // 2 - self.VERYSMALL - 10), "up", font=self.fonts[self.VERYSMALL],
                       fill=self.TEXT_COLOR, align="left")
        self.draw.text((15, self.sizey // 2 + 10), "dn", font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR,
                       align="left")
        if error_message:
            self.centered_text(40, error_message, self.VERYLARGE)
        self.bottom_line("", "", "Rst")

    def shutdown(countdown, shutdownmode):
        message = ""
        if shutdownmode == 0:   # shutdown stratux + display
            message = "Shutdown all"
        elif shutdownmode == 1:
            message = "Shtdwn displ"
        elif shutdownmode == 2:
            message = "Reboot"
        centered_text(0, message, largefont, fill="black")
        message = "in " + str(countdown) + " seconds!"
        centered_text(30, message, largefont, fill="black")
        message = "Left to cancel ..."
        centered_text(80, message, smallfont, fill="black")
        message = "Middle display only ..."
        centered_text(100, message, smallfont, fill="black")
        message = "Right for reboot all ..."
        centered_text(120, message, smallfont, fill="black")
        bottom_line("Canc", "Displ", "Rebo")


    def rollmarks(roll):
        if ah_zerox > ah_zeroy:
            di = ah_zeroy
        else:
            di = ah_zerox

        for rm in roll_posmarks:
            s = math.sin(math.radians(rm - roll + 90))
            c = math.cos(math.radians(rm - roll + 90))
            if rm % 30 == 0:
                draw.line((ah_zerox - di * c, ah_zeroy - di * s, ah_zerox - (di - 24) * c,
                           ah_zeroy - (di - 24) * s), fill="black", width=2)
            else:
                draw.line((ah_zerox - di * c, ah_zeroy - di * s, ah_zerox - (di - 16) * c,
                           ah_zeroy - (di - 16) * s), fill="black", width=2)
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
        slipsize = 8
        slipscale = 5
        if slipskid < -10:
            slipskid = -10
        elif slipskid > 10:
            slipskid = 10

        draw.rectangle((ah_zerox - 60, sizey - slipsize * 2, ah_zerox + 60, sizey - 1),
                       fill="black")
        draw.ellipse((ah_zerox - slipskid * slipscale - slipsize, sizey - slipsize * 2,
                      ah_zerox - slipskid * slipscale + slipsize, sizey - 1), fill="white")
        draw.line((ah_zerox, sizey - slipsize * 2, ah_zerox, sizey - 1), fill="black", width=4)
        draw.line((ah_zerox, sizey - slipsize * 2, ah_zerox, sizey - 1), fill="white", width=2)


    def ahrs(pitch, roll, heading, slipskid, error_message):
        # print("AHRS: pitch ", pitch, " roll ", roll, " heading ", heading, " slipskid ", slipskid)
        h1, h2 = linepoints(pitch, roll, 0, 300)  # horizon points
        h3, h4 = linepoints(pitch, roll, -180, 300)
        draw.polygon((h1, h2, h4, h3), fill="white")  # earth
        h3, h4 = linepoints(pitch, roll, 180, 300)
        draw.polygon((h1, h2, h4, h3), fill="white")  # sky
        draw.line((h1, h2), fill="black", width=4)  # horizon line

        earthfill = 0
        while earthfill > -180:
            earthfill -= 3
            draw.line((linepoints(pitch, roll, earthfill, 300)), fill="black", width=1)

        for pm in pitch_posmarks:  # pitchmarks
            draw.line((linepoints(pitch, roll, pm, 30)), fill="black", width=2)

        # pointer in the middle
        draw.line((ah_zerox - 90, ah_zeroy, ah_zerox - 30, ah_zeroy), width=4, fill="black")
        draw.line((ah_zerox + 90, ah_zeroy, ah_zerox + 30, ah_zeroy), width=4, fill="black")
        draw.polygon((ah_zerox, ah_zeroy + 4, ah_zerox - 20, ah_zeroy + 16, ah_zerox + 20, ah_zeroy + 16),
                     fill="black")

        # roll indicator
        rollmarks(roll)
        # slip indicator
        slip(slipskid)

        # infotext = "P:" + str(pitch) + " R:" + str(roll)
        if error_message:
            centered_text(60, error_message, smallfont, fill="black")
        bottom_line("Lev", "", "Zro")


    def text_screen(headline, subline, text, left_text, middle_text, right_text):
        centered_text(0, headline, morelargefont, fill="black")
        txt_starty = MORELARGE
        if subline is not None:
            centered_text(txt_starty, subline, largefont, fill="black")
            txt_starty += LARGE
        draw.text((0, txt_starty+4), text, font=smallfont, fill="black")
        bottom_line(left_text, middle_text, right_text)


    def screen_input(headline, subline, text, left, middle, right, prefix, inp, suffix):
        centered_text(0, headline, largefont, fill="black")
        txt_starty = LARGE
        if subline is not None:
            centered_text(LARGE, subline, smallfont, fill="black")
            txt_starty += LARGE
        bbox = draw.textbbox((0, txt_starty), text, font=smallfont)
        draw.text((0, txt_starty), text, font=smallfont, fill="black")
        bbox_p = draw.textbbox((bbox[0], bbox[3]), prefix, font=smallfont)
        draw.text((bbox[0], bbox[3]), prefix, fill="black", font=smallfont)
        bbox_rect = draw.textbbox((bbox_p[2], bbox[3]), inp, font=smallfont)
        draw.rectangle(bbox_rect, fill="black")
        draw.text((bbox_rect[0], bbox[3]), inp, font=smallfont, fill="white")
        draw.text((bbox_rect[2], bbox[3]), suffix, font=smallfont, fill="black")
        bottom_line(left, middle, right, offset=3)


    def bar(y, text, val, max_val, yellow, red, unit="", valtext=None, minval=0):
        bar_start = 50
        bar_end = 150

        draw.text((0, y), text, font=verysmallfont, fill="black", align="left")
        right_val = str(int(max_val)) + unit
        tl = draw.textlength(right_val, verysmallfont)
        draw.text((sizex-tl, y), right_val, font=verysmallfont, fill="black", align="right")
        draw.rounded_rectangle([bar_start-3, y-1, bar_end+3, y+VERYSMALL+1], radius=3, fill=None, outline="black", width=1)
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
        tl = draw.textlength(t, verysmallfont)
        draw.text(((bar_end-bar_start)/2+bar_start-tl/2, y), t, font=verysmallfont, fill="black",
                  stroke_width=1, stroke_fill="white")
        return y+VERYSMALL+6


    def round_text(x, y, text, color, yesno=True, out=None):
        tl = draw.textlength(text, verysmallfont)
        draw.rounded_rectangle([x, y-2, x+tl+10, y+VERYSMALL+3], radius=4, fill=color, outline=out)
        draw.text((x+5, y), text, font=verysmallfont, fill="black")
        if not yesno:
            draw.line([x, y+VERYSMALL+1, x+tl+5, y-1], fill="black", width=2)
        return x+tl+12


    def stratux(stat, altitude, gps_alt, gps_quality):
        starty = 0
        centered_text(0, "Stratux " + stat['version'], smallfont, fill="black")
        starty += SMALL + 4
        starty = bar(starty, "1090", stat['ES_messages_last_minute'], stat['ES_messages_max'], 0, 0)
        if stat['OGN_connected']:
            starty = bar(starty, "OGN", stat['OGN_messages_last_minute'], stat['OGN_messages_max'], 0, 0)
            noise_text = str(round(stat['OGN_noise_db'], 1)) + " dB"
            starty = bar(starty, "noise", stat['OGN_noise_db'], 25, 12, 18, unit="dB", minval=1, valtext=noise_text)
        if stat['UATRadio_connected']:
            starty = bar(starty, "UAT", stat['UAT_messages_last_minute'], stat['UAT_messages_max'], 0, 0)
        if stat['CPUTemp'] > -300:    # -300 means no value available
            starty = bar(starty, "temp", round(stat['CPUTemp'], 1), round(stat['CPUTempMax'], 0), 70, 80, "°C")
        # GPS
        if gps_quality == 1:
            t = "3D GPS "
        elif gps_quality == 2:
            t = "DGNSS "
        else:
            t = "GPS"
        draw.text((0, starty), t, font=verysmallfont, fill="black")

        t = str(stat['GPS_satellites_locked']) + "/" + \
            str(stat['GPS_satellites_seen']) + "/" + str(stat['GPS_satellites_tracked']) + " "
        draw.text((70, starty), t, font=verysmallfont, fill="black")
        if stat['GPS_position_accuracy'] < 19999:
            gps = str(round(stat['GPS_position_accuracy'], 1)) + "m"
        else:
            gps = "NoFix"
        right_text(starty, gps, verysmallfont, "black")
        starty += VERYSMALL+2

        draw.text((0, starty), "P-Alt {0:.0f}ft".format(altitude), font=verysmallfont, fill="black")
        right_text(starty, "Corr {0:+}ft".format(stat['AltitudeOffset']), verysmallfont, "black")
        starty += VERYSMALL + 6
        x = round_text(0, starty, "IMU", "white", stat['IMUConnected'], out="black")
        round_text(x+10, starty, "BMP", "white", stat['BMPConnected'], out="black")
        if stat['GPS_position_accuracy'] < 19999:
            alt = '{:5.0f}'.format(gps_alt)
        else:
            alt = " ---"
        right_text(starty, "GAlt" + alt + "ft", verysmallfont, "black")


    def flighttime(last_flights):
        starty = 0
        centered_text(0, "Flight Logs", smallfont, fill="black")
        starty += SMALL + 5

        draw.text((0, starty), "Date", font=verysmallfont, fill="black")
        draw.text((50, starty), "Start", font=verysmallfont, fill="black")
        draw.text((100, starty), "Dur", font=verysmallfont, fill="black")
        draw.text((155, starty), "Ldg", font=verysmallfont, fill="black")
        starty += VERYSMALL + 5

        maxlines = 6
        for f in last_flights:
            f[0] = f[0].replace(second=0, microsecond=0)   # round down start time to minutes
            draw.text((0, starty), f[0].strftime("%d.%m."), font=verysmallfont, fill="black")
            draw.text((50, starty), f[0].strftime("%H:%M"), font=verysmallfont, fill="black")
            if f[1] != 0:  # ==0 means still in the air
                f[1] = f[1].replace(second=0, microsecond=0)   # round down
                delta = (f[1] - f[0]).total_seconds()
                draw.text((155, starty), f[1].strftime("%H:%M"), font=verysmallfont, fill="black")
            else:
                delta = (datetime.datetime.now(datetime.timezone.utc).replace(second=0, microsecond=0)
                         - f[0]).total_seconds()
                draw.text((155, starty), "air", font=verysmallfont, fill="black")
            hours, remainder = divmod(delta, 3600)
            minutes, seconds = divmod(remainder, 60)
            out = '{:02}:{:02}'.format(int(hours), int(minutes))
            round_text(95, starty, out, "white", out="black")
            starty += VERYSMALL + 2
            maxlines -= 1
            if maxlines <= 0:
                break
        bottom_line("", "Mode", "Clear")


    def graph(xpos, ypos, xsize, ysize, data, minvalue, maxvalue, value_line1, value_line2, timeout):
        tl = draw.textlength(str(maxvalue), verysmallfont)    # for adjusting x and y
        # adjust zero lines to have room for text
        xpos = xpos + tl + space
        xsize = xsize - tl - space
        ypos = ypos + VERYSMALL/2
        ysize = ysize - VERYSMALL

        vlmin_y = ypos + ysize - 1
        tl = draw.textlength(str(minvalue), verysmallfont)
        draw.text((xpos - tl - space, vlmin_y - VERYSMALL), str(minvalue), font=verysmallfont, fill="black")

        vl1_y = ypos + ysize - ysize * (value_line1 - minvalue) / (maxvalue - minvalue)
        tl = draw.textlength(str(value_line1), verysmallfont)
        draw.text((xpos - tl - space, vl1_y - VERYSMALL/2), str(value_line1), font=verysmallfont, fill="black")

        vl2_y = ypos + ysize - ysize * (value_line2 - minvalue) / (maxvalue - minvalue)
        tl = draw.textlength(str(value_line2), verysmallfont)
        draw.text((xpos - tl - space, vl2_y - VERYSMALL/2), str(value_line2), font=verysmallfont, fill="black")

        vlmax_y = ypos
        tl = draw.textlength(str(maxvalue), verysmallfont)
        draw.text((xpos - tl - space, vlmax_y - VERYSMALL/2), str(maxvalue), font=verysmallfont, fill="black")

        draw.rectangle((xpos, ypos, xpos+xsize-1, ypos+ysize-1), outline="black", width=3, fill="white")

        # values below x-axis
        no_of_values = len(data)
        full_time = timeout * no_of_values   # time for full display in secs
        timestr = time.strftime("%H:%M", time.gmtime())
        tl = draw.textlength(timestr, verysmallfont)
        no_of_time = math.floor(xsize / tl / 2) + 1   # calculate maximum number of time indications
        time_offset = full_time / no_of_time
        offset = math.floor((xsize-1) / no_of_time)
        x = xpos
        acttime = math.floor(time.time())
        for i in range(0, no_of_time+1):
            draw.line((x, ypos+ysize-1-5, x, ypos+ysize-1+3), width=2, fill="black")
            timestr = time.strftime("%H:%M", time.gmtime(math.floor(acttime - (no_of_time-i) * time_offset)))
            draw.text((x - tl/2, ypos+ysize-1 + 1), timestr, font=verysmallfont, fill="black")
            x = x + offset
        lastpoint = None
        for i in range(0, len(data)):
            y = math.floor(ypos-1 + ysize - ysize * (data[i] - minvalue) / (maxvalue - minvalue))
            if y < ypos:
                y = ypos   # if value is outside
            if y > ypos+ysize-1:
                x = ypos+ysize-1
            if i >= 1:  # we need at least two points before we draw
                x = math.floor(xpos + i * xsize / (len(data)-1))
                draw.line([lastpoint, (x, y)], fill="black", width=2)
            else:
                x = xpos
            lastpoint = (x, y)
        # value_line 1
        y = math.floor(ypos + ysize - ysize * (value_line1 - minvalue) / (maxvalue - minvalue))

        for x in range(int(xpos), int(xpos+xsize), 6):
            draw.line([(x, y), (x + 3, y)], fill="black", width=1)
        # value_line 2
        y = math.floor(ypos + ysize - ysize * (value_line2 - minvalue) / (maxvalue - minvalue))
        for x in range(int(xpos), int(xpos+xsize), 6):
            draw.line([(x, y), (x + 3, y)], fill="black", width=1)


    def cowarner(co_values, co_max, r0, timeout, alarmlevel, alarmppm, alarmperiod):   # draw graph and co values
        if alarmlevel == 0:
            centered_text(0, "CO: No CO alarm", smallfont, fill="black")
        else:
            if alarmperiod > 60:
                alarmstr = "CO: {:d}ppm>{:d}min".format(alarmppm, math.floor(alarmperiod/60))
            else:
                alarmstr = "CO: {:d}ppm>{:d} sec".format(alarmppm, math.floor(alarmperiod))
            centered_text(0, alarmstr, smallfont, fill="black")
        graph(0, SMALL+5, sizex-19, sizey-80, co_values, 0, 120, 50, 100, timeout)

        if len(co_values) > 0:
            round_text(5, sizey-2*SMALL, "act: {:3d}".format(co_values[len(co_values)-1]), "white", out="black")
        round_text(sizex/2+5, sizey-2*SMALL, "max: {:3d}".format(co_max), "white", out="black")
        bottom_line("Cal", "Mode", "Reset")


    def dashboard(x, y, sizex, lines):
        # dashboard, arguments are lines = ("text", "value"), ....
        starty = y
        for line in lines:
            draw.text((x, starty), line[0], font=smallfont, fill="black", align="left")
            tl = draw.textlength(line[1], smallfont)
            draw.text((x+sizex-tl, starty), line[1], font=smallfont, fill="black")
            starty += SMALL+2
        return starty


    def distance(now, gps_valid, gps_quality, gps_h_accuracy, distance_valid, gps_distance, gps_speed, baro_valid,
                 own_altitude, alt_diff, alt_diff_takeoff, vert_speed, ahrs_valid, ahrs_pitch, ahrs_roll,
                 ground_distance_valid, grounddistance, error_message):
        centered_text(0, "GPS-Distance", smallfont, fill="black")
        gps_dist_str = "---"
        gps_speed_str = "---"
        if distance_valid:
            gps_dist_str = "{:4.0f}".format(gps_distance)
        if gps_valid:
            gps_speed_str = "{:3.1f}".format(gps_speed)
        lines = (
            ("UTC", "{:0>2d}:{:0>2d}:{:0>2d},{:1d}".format(now.hour, now.minute, now.second,
                                                           math.floor(now.microsecond / 100000))),
            ("GPS-Dist [m]", gps_dist_str),
            ("GPS-Spd [kts]", gps_speed_str),
        )
        starty = dashboard(0, SMALL+2, sizex, lines)
        if baro_valid:
            if alt_diff_takeoff is not None:
                takeoff_str = "{:+5.1f}".format(alt_diff_takeoff)
            else:
                takeoff_str = "---"
            lines = (
                ("VSpeed [ft]", "{:+4.0f}".format(vert_speed)),
                ("BaDif tof [ft]", takeoff_str),
            )
            starty = dashboard(0, starty, sizex, lines)
        if ground_distance_valid:
            lines = (
                ("GrdDist [cm]", "{:+3.1f}".format(grounddistance/10)),
            )
            dashboard(0, starty, sizex, lines)
        if error_message is not None:
            centered_text(80, error_message, verylargefont, fill="black")
        bottom_line("Stats/Set", "  Mode", "Start")


    def form_line(values, key, format_str):    # generates line if key exists with form string, "---" else
        if key in values:
            return format_str.format(values[key])
        else:
            return '---'


    def distance_statistics(values, gps_valid, gps_altitude, dest_altitude, dest_alt_valid, ground_warnings):
        centered_text(0, "Start-/Landing", smallfont, fill="black")

        st = '---'
        if 'start_time' in values:
            st = "{:0>2d}:{:0>2d}:{:0>2d},{:1d}".format(values['start_time'].hour, values['start_time'].minute,
                                                        values['start_time'].second,
                                                        math.floor(values['start_time'].microsecond / 100000))
        lines = (
            ("t-off time", st),
            ("t-off dist [m]", form_line(values, 'takeoff_distance', "{:3.1f}")),
            ("obst dist [m]", form_line(values, 'obstacle_distance_start', "{:3.1f}")),
        )
        starty = dashboard(0, SMALL + 2, sizex, lines)

        lt = '---'
        if 'landing_time' in values:
            lt = "{:0>2d}:{:0>2d}:{:0>2d},{:1d}".format(values['landing_time'].hour, values['landing_time'].minute,
                                                        values['landing_time'].second,
                                                        math.floor(values['landing_time'].microsecond / 100000))
        lines = (
            ("ldg time", lt),
            ("ldg dist [m]", form_line(values, 'landing_distance', "{:3.1f}")),
            ("obst dist [m]", form_line(values, 'obstacle_distance_landing', "{:3.1f}")),
        )
        starty = dashboard(0, starty, sizex, lines)

        if ground_warnings:
            if dest_alt_valid:
                dest_alt_str = "{:+5.0f}".format(dest_altitude)
            else:
                dest_alt_str = "---"

            lines = (
                ("Dest. Alt [ft]", dest_alt_str),
            )
            dashboard(0, starty, sizex, lines)
        if not ground_warnings:
            bottom_line("", "Back", "")
        else:
            bottom_line("+/-100ft", "  Back", "+/-10ft")


    def checklist_topic(ypos, topic, highlighted=False, toprint=True):
        xpos = 2
        xpos_remark = 20
        xpos_sub = 20
        topic_offset = 2
        subtopic_offset = 3
        remark_offset = 2
        topic_right_offset = 3

        y = ypos
        if 'TASK' in topic and topic['TASK'] is not None:
            if toprint:
                draw.text((xpos, ypos), topic['TASK'], font=verysmallfont, fill="black")  # Topic
        if 'CHECK' in topic and topic['CHECK'] is not None:
            if toprint:
                right_text(ypos, topic['CHECK'], font=verysmallfont, fill="black", offset=topic_right_offset)
        y += SMALL
        if 'REMARK' in topic and topic['REMARK'] is not None:  # remark
            y += remark_offset
            if toprint:
                draw.text((xpos_remark, y), topic['REMARK'], font=verysmallfont, fill="black")  # remark
            y += VERYSMALL
        if 'TASK1' in topic and topic['TASK1'] is not None:  # subtopic
            y += subtopic_offset
            if toprint:
                draw.text((xpos_sub, y), topic['TASK1'], font=verysmallfont, fill="black")  # subtopic
            if 'CHECK1' in topic and topic['CHECK1'] is not None:
                if toprint:
                    right_text(y, topic['CHECK1'], font=smallfont, fill="black", offset=topic_right_offset)
            y += VERYSMALL
        if 'TASK2' in topic and topic['TASK2'] is not None:  # subtopic2
            y += subtopic_offset
            if toprint:
                draw.text((xpos_sub, y), topic['TASK2'], font=verysmallfont, fill="black")  # subtopic
            if 'CHECK2' in topic and topic['CHECK2'] is not None:
                if toprint:
                    right_text(y, topic['CHECK2'], font=verysmallfont, fill="black", offset=topic_right_offset)
            y += VERYSMALL
        if 'TASK3' in topic and topic['TASK3'] is not None:  # subtopic3
            y += subtopic_offset
            if toprint:
                draw.text((xpos_sub, y), topic['TASK3'], font=verysmallfont, fill="black")  # subtopic
            if 'CHECK3' in topic and topic['CHECK3'] is not None:
                if toprint:
                    right_text(y, topic['CHECK3'], font=verysmallfont, fill="black", offset=topic_right_offset)
            y += VERYSMALL
        if highlighted:  # draw frame around whole topic
            if toprint:
                draw.rounded_rectangle([0, ypos - 1, sizex-1, y + 1], width=1, radius=3, outline="black")
        return y + topic_offset


    def checklist(checklist_name, checklist_items, current_index, last_list):
        checklist_y = {'from': SMALL + 8, 'to': sizey - VERYSMALL - 6}
        global top_index

        centered_text(0, checklist_name, smallfont, fill="black")
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
            left = "PrevL"
        else:
            left = "Prev"
        if last_list and current_index == len(checklist_items) - 1:  # last_item
            bottom_line("Prev", "Mode", "")
        elif last_list:
            bottom_line(left, "Mode", "Check")
        else:
            bottom_line(left, "NxtList", "Check")



# instantiate a single object in the file, needs to be done and inherited in every display module
radar_display = Epaper1in54()