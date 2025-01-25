#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK
#
# BSD 3-Clause License
# Copyright (c) 2024, Thomas Breitbach
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
import time
import logging
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# helper functions
def posn(angle, arm_length, angle_offset=0):
    dx = round(math.cos(math.radians(angle_offset + angle)) * arm_length)
    dy = round(math.sin(math.radians(angle_offset + angle)) * arm_length)
    return dx, dy


def turn(sin_a, cos_a, p, zero):
    return round(zero[0] + p[0] * cos_a - p[1] * sin_a), round(zero[1] + p[0] * sin_a + p[1] * cos_a)


def translate(angle, points, zero):
    s = math.sin(math.radians(angle))
    c = math.cos(math.radians(angle))
    result = tuple(turn(s, c, p, zero) for p in points)
    return result


class GenericDisplay:
    # display specific constants, overwrite for every display!
    VERYLARGE = 48  # timer
    MORELARGE = 36
    LARGE = 30  # size of height indications of aircraft
    SMALL = 24  # size of information indications on top and bottom
    VERYSMALL = 18
    AWESOME_FONTSIZE = 18  # bluetooth indicator
    # radar-mode
    AIRCRAFT_SIZE = 6  # size of aircraft arrow
    AIRCRAFT_COLOR = "red"
    BG_COLOR = "black"
    TEXT_COLOR = "white"   # default color for text
    VELOCITY_WIDTH = 3  # width of indicator for velocity of aircraft
    MINIMAL_CIRCLE = 20  # minimal size of mode-s circle
    ARCPOSITION_EXCLUDE_FROM = 0
    ARCPOSITION_EXCLUDE_TO = 0
    ANGLE_OFFSET = 270  # offset for calculating angles in displays
    UP_CHARACTER = '\u2197'     # character to show ascending aircraft
    DOWN_CHARACTER = '\u2198'   # character to show descending aircraft
    # AHRS specific constants
    ROLL_POSMARKS = (-90, -60, -30, -20, -10, 0, 10, 20, 30, 60, 90)
    PITCH_POSMARKS = (-30, -20, -10, 10, 20, 30)
    PITCH_SCALE = 3.0   # larger displays need larger scaling
    # COMPASS specific constants
    CM_SIZE = 15  # length of compass marks
    # CO warner specific constants
    GRAPH_SPACE = 3  # space between scale figures and zero line
    GRAPH_X_AXIS_LINE_LENGTH = 5  # line length for values in graph
    # end constant definitions


    def __init__(self):
        self.rlog = logging.getLogger('stratux-radar-log')
        # these variables below need to be set for every display!
        self.sizex = 0  # display size x axis in pixel
        self.sizey = 0  # display size y axis in pixel
        self.zerox = 0  # zero position (center) in pixel (typically half of sizex)
        self.zeroy = 0  # zero position y-axis in pixel (typically half of sizex)
        self.ah_zerox = 0  # zero point x for ahrs
        self.ah_zeroy = 0  # zero point x for ahrs
        self.max_pixel = 0  # maximum pixel size which is typicall max(sizex, sizey)
        self.display_refresh = 0.1  # display refresh time, is to be calculated or set in init
        self.arcposition = 0    # angle where the height for mode-s targets is displayed on the arc
        self.draw = None  # pixel array to be used for draw functions generally
        self.cdraw = None  # pixel array to be used in compass to delete text
        self.compass_aircraft = None    # image of the compass aircraft
        # fonts
        self.verylargefont = GenericDisplay.make_font("Font.ttc", self.VERYLARGE)
        self.morelargefont = GenericDisplay.make_font("Font.ttc", self.MORELARGE)
        self.largefont = GenericDisplay.make_font("Font.ttc", self.LARGE)  # font for height indications
        self.smallfont = GenericDisplay.make_font("Font.ttc", self.SMALL)  # font for information indications
        self.verysmallfont = GenericDisplay.make_font("Font.ttc", self.VERYSMALL)  # font for information indications
        self.awesomefont = GenericDisplay.make_font("fontawesome-webfont.ttf", self.AWESOME_FONTSIZE)  # for bluetooth indicator

    def init(self, fullcircle=False):    # explicit init to be implemented for every device type
        # set device properties
        self.rlog.debug("Running Radar with NoDisplay! ")
        return self.max_pixel, self.zerox, self.zeroy, self.display_refresh

    def modesaircraft(self, radius, height, arcposition, vspeed, tail, width=3):
        if radius < self.MINIMAL_CIRCLE:
            radius = self.MINIMAL_CIRCLE
        self.draw.ellipse((self.zerox-radius, self.zeroy-radius, self.zerox+radius, self.zeroy+radius),
                          width=width, outline=self.AIRCRAFT_COLOR)
        arctext = posn(arcposition, radius, angle_offset=self.ANGLE_OFFSET)
        if height > 0:
            signchar = "+"
        else:
            signchar = "-"
        t = signchar+str(abs(height))
        if vspeed > 0:
            t = t + self.UP_CHARACTER
        if vspeed < 0:
            t = t + self.DOWN_CHARACTER
        w = self.draw.textlength(t, self.largefont)
        tposition = (int(self.zerox+arctext[0]-w/2), int(self.zeroy+arctext[1]-self.LARGE/2))
        self.draw.rectangle((tposition, (tposition[0]+w, tposition[1]+self.LARGE+2)), fill=self.BG_COLOR)
        self.draw.text(tposition, t, font=self.largefont, fill=self.AIRCRAFT_COLOR)
        if tail is not None:
            tl = self.draw.textlength(tail, self.verysmallfont)
            self.draw.rectangle((tposition[0], tposition[1] + self.LARGE, tposition[0] + tl,
                            tposition[1] + self.LARGE + self.VERYSMALL), fill=self.BG_COLOR)
            self.draw.text((tposition[0], tposition[1] + self.LARGE), tail,
                           font=self.verysmallfont, fill=self.AIRCRAFT_COLOR)

    def aircraft(self, x, y, direction, height, vspeed, nspeed_length, tail, angle_offset=0):
        p1 = posn(direction, 2 * self.AIRCRAFT_SIZE, angle_offset)
        p2 = posn(direction + 150, 4 * self.AIRCRAFT_SIZE, angle_offset)
        p3 = posn(direction + 180, 2 * self.AIRCRAFT_SIZE, angle_offset)
        p4 = posn(direction + 210, 4 * self.AIRCRAFT_SIZE, angle_offset)
        p5 = posn(direction, nspeed_length, angle_offset)  # line for speed

        self.draw.polygon(
            ((x + p1[0], y + p1[1]), (x + p2[0], y + p2[1]), (x + p3[0], y + p3[1]), (x + p4[0], y + p4[1])),
            fill=self.AIRCRAFT_COLOR, outline=self.AIRCRAFT_COLOR)
        self.draw.line((x + p1[0], y + p1[1], x + p5[0], y + p5[1]), fill=self.AIRCRAFT_COLOR, width=self.VELOCITY_WIDTH)
        if height >= 0:
            t = "+" + str(abs(height))
        else:
            t = "-" + str(abs(height))
        if vspeed > 0:
            t = t + self.UP_CHARACTER
        if vspeed < 0:
            t = t + self.DOWN_CHARACTER
        w = self.draw.textlength(t, self.largefont)
        if w + x + 4 * self.AIRCRAFT_SIZE - 2 > self.sizex:
            # would draw text outside, move to the left
            tposition = (x - 4 * self.AIRCRAFT_SIZE - w, int(y - self.LARGE / 2))
        else:
            tposition = (x + 4 * self.AIRCRAFT_SIZE + 1, int(y - self.LARGE / 2))
        self.draw.text(tposition, t, font=self.largefont, fill=self.AIRCRAFT_COLOR)
        if tail is not None:
            self.draw.text((tposition[0], tposition[1] + self.LARGE), tail, font=self.verysmallfont, fill=self.AIRCRAFT_COLOR)


    def display(self):
        pass

    def is_busy(self):
        pass


    @staticmethod
    def next_arcposition(old_arcposition, exclude_from=0, exclude_to=0):
        # defines next position of height indicator on circle. Can be used to exclude several ranges or
        # be used to define the next angle on the circle
        new_arcposition = (old_arcposition + 210) % 360
        if exclude_to > 0 or exclude_from > 0:
            if exclude_to >= new_arcposition >= exclude_from:
                new_arcposition = (new_arcposition + 210) % 360
        return new_arcposition

    def clear(self):
        pass

    def cleanup(self):
        pass

    def refresh(self):
        pass

    def startup(self, version, target_ip, seconds):
        pass

    def situation(self, connected, gpsconnected, ownalt, course, rrange, altdifference, bt_devices, sound_active,
                  gps_quality, gps_h_accuracy, optical_bar, basemode, extsound, co_alarmlevel, co_alarmstring):
        pass

    def timer(self, utctime, stoptime, laptime, laptime_head, left_text, middle_text, right_t, timer_runs,
              utc_color=None, timer_color=None, second_color=None):
        if utc_color is None:
            utc_color = self.TEXT_COLOR
        if timer_color is None:
            timer_color = self.TEXT_COLOR
        if second_color is None:
            second_color = self.TEXT_COLOR
        self.draw.text((5, 0), "UTC", font=self.smallfont, fill=self.TEXT_COLOR)
        self.centered_text(self.SMALL, utctime, self.verylargefont, color=utc_color)
        if stoptime is not None:
            self.draw.text((5, self.SMALL + self.VERYLARGE), "Timer", font=self.smallfont, fill=self.TEXT_COLOR)
            self.centered_text(2 * self.SMALL + self.VERYLARGE, stoptime, self.verylargefont, color=timer_color)
            if laptime is not None:
                self.draw.text((5, 2 * self.SMALL + 2 * self.VERYLARGE), laptime_head, font=self.smallfont,
                               fill=self.TEXT_COLOR)
                self.centered_text(3 * self.SMALL + 2 * self.VERYLARGE, laptime, self.verylargefont, color=second_color)
        self.bottom_line(left_text, middle_text, right_t)


    def gmeter(self, current, maxg, ming, error_message):
        pass

    def compass(self, heading, error_message):
        pass

    def vsi(self, vertical_speed, flight_level, gps_speed, gps_course, gps_altitude, vertical_max, vertical_min,
            error_message):
        pass

    def shutdown(self, countdown, shutdownmode):
        pass

    def ahrs(self, pitch, roll, heading, slipskid, error_message):
        pass

    def text_screen(self, headline, subline, text, left_text, middle_text, r_text):
        pass

    def screen_input(self, headline, subline, text, left, middle, right, prefix, inp, suffix):
        pass

    def stratux(self, stat, altitude, gps_alt, gps_quality):
        pass

    def flighttime(self, last_flights):
        pass

    def cowarner(self, co_values, co_max, r0, timeout, alarmlevel, alarmppm, alarmperiod):  # draw graph and co values
        pass

    def distance(self, now, gps_valid, gps_quality, gps_h_accuracy, distance_valid, gps_distance, gps_speed, baro_valid,
                 own_altitude, alt_diff, alt_diff_takeoff, vert_speed, ahrs_valid, ahrs_pitch, ahrs_roll,
                 ground_distance_valid, grounddistance, error_message):
        pass

    def distance_statistics(self, values, gps_valid, gps_altitude, dest_altitude, dest_alt_valid, ground_warnings):
        pass

    def checklist(self, checklist_name, checklist_items, current_index, last_list):
        pass

    ####################################
    # Generic support functions
    ####################################
    @staticmethod
    def make_font(name, size):
        font_path = str(Path(__file__).resolve().parent.joinpath('fonts', name))
        return ImageFont.truetype(font_path, size)

    @staticmethod
    def form_line(values, key, format_str):  # generates line if key exists with form string, "---" else
        if key in values:
            return format_str.format(values[key])
        else:
            return '---'

    def centered_text(self, y, text, font, color=None):
        if color is None:
            color = self.TEXT_COLOR
        tl = self.draw.textlength(text, font)
        self.draw.text((math.floor(self.zerox - tl / 2), y), text, font=font, fill=color)

    def right_text(self, y, text, font, color=None, offset=0):
        if color is None:
            color = self.TEXT_COLOR
        tl = self.draw.textlength(text, font)
        self.draw.text((self.sizex - 5 - tl - offset, y), text, font=font, fill=color)


    def bottom_line(self, left, middle, right, color=None, offset_bottom=3, offset_left=3, offset_right=3):
        y = self.sizey - self.smallfont.size - offset_bottom
        if color is None:
            color = self.TEXT_COLOR
        self.draw.text((offset_left, y), left,
                       font=self.smallfont, fill=color)
        textlength = self.draw.textlength(right, self.smallfont)
        self.draw.text((self.sizex - textlength - offset_right, y), right,
                       font=self.smallfont, fill=color, align="right")
        self.centered_text(y, middle, self.smallfont, color)

    def graph(self, xpos, ypos, xsize, ysize, data, minvalue, maxvalue, value_line1, value_line2, timeout,
              textcolor, graphcolor, linecolor, bgcolor, glinewidth, linewidth, x_val_space, x_val_linelength):
        # textcolor = text in graph, graphcolor = graph itself, linecolor = lines outside, linewidth=lines outside
        # glinewidth = graph linewidth
        # valueline= value for a line (threshold 1+2)
        # x_val_space = space between x values below and x-axis
        # x_val_linelength = length of lines at axis valuepoints up and down of x-axis
        tl = math.floor(self.draw.textlength(str(maxvalue), verysmallfont))  # for adjusting x and y
        # adjust zero lines to have room for text
        xpos = xpos + tl + x_val_space
        xsize = xsize - tl - x_val_space
        ypos = math.floor(ypos + VERYSMALL / 2)
        ysize = ysize - VERYSMALL

        vlmin_y = ypos + ysize - 1
        tl = math.floor(self.draw.textlength(str(minvalue), verysmallfont))
        self.draw.text((xpos - tl - x_val_space, vlmin_y - VERYSMALL), str(minvalue), font=verysmallfont, fill=textcolor)

        vl1_y = math.floor(ypos + ysize - ysize * (value_line1 - minvalue) / (maxvalue - minvalue))
        tl = self.draw.textlength(str(value_line1), verysmallfont)
        self.draw.text((xpos - tl - x_val_space, math.floor(vl1_y - VERYSMALL / 2)), str(value_line1),
                  font=verysmallfont, fill=textcolor)
        vl2_y = math.floor(ypos + ysize - ysize * (value_line2 - minvalue) / (maxvalue - minvalue))
        tl = self.draw.textlength(str(value_line2), verysmallfont)
        self.draw.text((xpos - tl - x_val_space, math.floor(vl2_y - VERYSMALL / 2)), str(value_line2),
                  font=verysmallfont, fill=textcolor)

        vlmax_y = ypos
        # outside text and frame
        tl = self.draw.textlength(str(maxvalue), verysmallfont)
        self.draw.text((xpos - tl - x_val_space, math.floor(vlmax_y - VERYSMALL / 2)), str(maxvalue), font=verysmallfont,
                  fill=textcolor)
        self.draw.rectangle((xpos, ypos, xpos + xsize, ypos + ysize), outline=linecolor, width=linewidth, fill=bgcolor)
        # values below x-axis
        no_of_values = len(data)
        full_time = timeout * no_of_values  # time for full display in secs
        timestr = time.strftime("%H:%M", time.gmtime())
        tl = self.draw.textlength(timestr, verysmallfont)
        no_of_time = math.floor(xsize / tl / 2) + 1  # calculate maximum number of time indications
        time_offset = full_time / no_of_time
        offset = math.floor((xsize - 1) / no_of_time)
        x = xpos
        acttime = math.floor(time.time())
        # draw values below x-axis
        for i in range(0, no_of_time + 1):
            self.draw.line((x, ypos+ysize-1 + x_val_linelength, x, ypos+ysize-1 - x_val_linelength),
                           width=linewidth, fill=linecolor)
            timestr = time.strftime("%H:%M", time.gmtime(math.floor(acttime - (no_of_time - i) * time_offset)))
            self.draw.text((math.floor(x - tl / 2), ypos + ysize - 1 + 1), timestr, font=verysmallfont, fill=textcolor)
            x = x + offset
        lastpoint = None
        for i in range(0, len(data)):
            y = math.floor(ypos - 4 + ysize - ysize * (data[i] - minvalue) / (maxvalue - minvalue))
            if y < ypos:
                y = ypos  # if value is outside
            if y > ypos + ysize - 1:
                y = ypos + ysize - 1 # if value is outside
            if i >= 1:  # we need at least two points before we draw
                x = math.floor(xpos + i * xsize / (len(data) - 1))
                self.draw.line([lastpoint, (x, y)], fill=graphcolor, width=glinewidth)
            else:
                x = xpos
            lastpoint = (x, y)
        # value_line 1, dashed line
        y = math.floor(ypos + ysize - ysize * (value_line1 - minvalue) / (maxvalue - minvalue))
        for x in range(int(xpos), int(xpos + xsize), 6):
            self.draw.line([(x, y), (x + 3, y)], fill=linecolor, width=linewidth)
        # value_line 2, dashed line
        y = math.floor(ypos + ysize - ysize * (value_line2 - minvalue) / (maxvalue - minvalue))
        for x in range(int(xpos), int(xpos + xsize), 6):
            self.draw.line([(x, y), (x + 3, y)], fill=linecolor, width=linewidth)

    def dashboard(self, x, y, dsizex, lines, color, bgcolor, rounding=False, headline=None):
        # dashboard, arguments are lines = ("text", "value"), ....
        starty = y + VERYSMALL / 2
        for line in lines:
            self.draw.text((x + 7, starty + (SMALL - VERYSMALL) / 2), line[0], font=verysmallfont, fill=color,
                      align="left")
            tl = self.draw.textlength(line[1], self.smallfont)
            self.draw.text((x + dsizex - 7 - tl, starty), line[1], font=smallfont, fill=color)
            starty += SMALL + 3
        if rounding:
            starty += VERYSMALL / 2
            self.draw.rounded_rectangle([x, y, x + dsizex, starty], radius=6, fill=None, outline=color, width=2)
            tl = self.draw.textlength(headline, verysmallfont)
            self.draw.rectangle([x + 20, y - SMALL / 2, x + 20 + tl + 8, y + SMALL / 2], fill=bgcolor, outline=None)
        self.draw.text((x + 20 + 4, y - VERYSMALL / 2), headline, font=verysmallfont, fill=color)
        return starty

    def meter(self, current, start_value, end_value, from_degree, to_degree, size, center_x, center_y,
              marks_distance, small_marks_distance, middle_text1, middle_text2):
        big_mark_length = int(min(sizex, sizey)/20)
        small_mark_length = int(min(sizex, sizey)/40)
        text_distance = small_mark_length
        arrow_line_size = int(small_mark_length * 1.5)
        arrow_head_size = small_mark_length
        arrow_distance = int(arrow_head_size/2)  # distance from arrow to outside values

        arrow = ((int(arrow_line_size/2), 0), (int(-arrow_line_size/2), 0), (int(-arrow_line_size/2),
            int(-size/2) + arrow_head_size), (0, int(-size/2) + arrow_distance), (int(arrow_line_size/2),
            int(-size/2) + arrow_head_size), (int(arrow_line_size/2), 0))
        # points of arrow at angle 0 (pointing up) for line drawing

        deg_per_value = (to_degree - from_degree) / (end_value - start_value)

        self.draw.arc((center_x - size / 2, center_y - size / 2, center_x + size / 2, center_y + size / 2),
                 from_degree - 90, to_degree - 90, width=6, fill="black")
        # small marks first
        line = ((0, -size / 2 + 1), (0, -size / 2 + small_mark_length))
        m = start_value
        while m <= end_value:
            angle = deg_per_value * (m - start_value) + from_degree
            mark = translate(angle, line, (center_x, center_y))
            self.draw.line(mark, fill="black", width=2)
            m += small_marks_distance
        # large marks
        line = ((0, -size / 2 + 1), (0, -size / 2 + big_mark_length))
        m = start_value
        while m <= end_value:
            angle = deg_per_value * (m - start_value) + from_degree
            mark = translate(angle, line, (center_x, center_y))
            self.draw.line(mark, fill="black", width=4)
            # text
            marktext = str(m)
            tl = self.draw.textlength(marktext, self.largefont)
            t_center = translate(angle, ((0, -size / 2 + big_mark_length + self.LARGE / 2 + text_distance),),
                                 (center_x, center_y))
            self.draw.text((t_center[0][0] - tl / 2, t_center[0][1] - self.LARGE / 2), marktext, fill="black", font=largefont)
            m += marks_distance
        # arrow
        if current > end_value:  # normalize values in allowed ranges
            current = end_value
        elif current < start_value:
            current = start_value
        angle = deg_per_value * (current - start_value) + from_degree
        ar = translate(angle, arrow, (center_x, center_y))
        self.draw.line(ar, fill="black", width=4)
        # centerpoint
        self.draw.ellipse((center_x - 10, center_y - 10, center_x + 10, center_y + 10), fill="black")

        if middle_text1 is not None:
            tl = draw.textlength(middle_text1, self.smallfont)
            self.draw.text((center_x - tl / 2, center_y - SMALL - 20), middle_text1, font=smallfont, fill="black",
                      align="left")
        if middle_text2 is not None:
            tl = draw.textlength(middle_text2, self.smallfont)
            self.draw.text((center_x - tl / 2, center_y + 20), middle_text2, font=self.smallfont, fill="black", align="left")

