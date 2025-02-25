#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK
#
# BSD 3-Clause License
# Copyright (c) 2025, Thomas Breitbach
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
import datetime
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
    AWESOME_FONTSIZE= 18  # bluetooth indicator
    # radar-mode
    AIRCRAFT_SIZE = 6  # size of aircraft arrow
    AIRCRAFT_COLOR = "red"
    MODE_S_COLOR = "white"
    AIRCRAFT_OUTLINE = "white"
    BG_COLOR = "black"
    TEXT_COLOR = "white"   # default color for text
    HIGHLIGHT_COLOR = TEXT_COLOR
    # AHRS
    AHRS_EARTH_COLOR = "brown"   # how ahrs displays the earth
    AHRS_SKY_COLOR = "blue"   # how ahrs displays the sky
    AHRS_HORIZON_COLOR = "white"   # color of horizon line in ahrs
    AHRS_MARKS_COLOR = "white"   # color of marks and corresponding text in ahrs
    # RADAR
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
        self.fonts= {
            self.VERYLARGE: self.make_font("Font.ttc", self.VERYLARGE),
            self.MORELARGE: self.make_font("Font.ttc", self.MORELARGE),
            self.LARGE: self.make_font("Font.ttc", self.LARGE),
            self.SMALL: self.make_font("Font.ttc", self.SMALL),
            self.VERYSMALL: self.make_font("Font.ttc", self.VERYSMALL)
        }
        self.awesomefont = self.make_font("fontawesome-webfont.ttf", self.AWESOME_FONTSIZE)

    def init(self, fullcircle=False):    # explicit init to be implemented for every device type
        # set device properties
        self.rlog.debug("Running Radar with NoDisplay! ")
        return self.max_pixel, self.zerox, self.zeroy, self.display_refresh

    def modesaircraft(self, radius, height, arcposition, vspeed, tail):
        circle_width = max(2, 1 + self.max_pixel // 128)
        if radius < self.MINIMAL_CIRCLE:
            radius = self.MINIMAL_CIRCLE
        self.draw.ellipse((self.zerox-radius, self.zeroy-radius, self.zerox+radius, self.zeroy+radius),
                          width=circle_width, outline=self.MODE_S_COLOR)
        arctext = posn(arcposition, radius, angle_offset=self.ANGLE_OFFSET)
        signchar = "+" if height > 0 else "-"
        t = signchar + str(abs(height))
        t += self.UP_CHARACTER if vspeed > 0 else self.DOWN_CHARACTER if vspeed < 0 else ""
        w = self.draw.textlength(t, self.fonts[self.LARGE])
        tposition = (int(self.zerox+arctext[0]-w//2), int(self.zeroy+arctext[1]-self.LARGE//2))
        self.draw.rectangle((tposition, (tposition[0]+w, tposition[1]+self.LARGE)), fill=self.BG_COLOR)
        self.draw.text(tposition, t, font=self.fonts[self.LARGE], fill=self.MODE_S_COLOR)
        if tail is not None:
            tl = self.draw.textlength(tail, self.fonts[self.VERYSMALL])
            self.draw.rectangle((tposition[0], tposition[1] + self.LARGE, tposition[0] + tl,
                            tposition[1] + self.LARGE + self.VERYSMALL), fill=self.BG_COLOR)
            self.draw.text((tposition[0], tposition[1] + self.LARGE), tail,
                           font=self.fonts[self.VERYSMALL], fill=self.MODE_S_COLOR)

    def aircraft(self, x, y, direction, height, vspeed, nspeed_length, tail):
        velocity_width = max(2, 1 + self.AIRCRAFT_SIZE // 3)
        p1 = posn(direction, 2 * self.AIRCRAFT_SIZE, self.ANGLE_OFFSET)
        p2 = posn(direction + 150, 4 * self.AIRCRAFT_SIZE, self.ANGLE_OFFSET)
        p3 = posn(direction + 180, 2 * self.AIRCRAFT_SIZE, self.ANGLE_OFFSET)
        p4 = posn(direction + 210, 4 * self.AIRCRAFT_SIZE, self.ANGLE_OFFSET)
        p5 = posn(direction, nspeed_length, self.ANGLE_OFFSET)  # line for speed

        self.draw.polygon(
            ((x + p1[0], y + p1[1]), (x + p2[0], y + p2[1]), (x + p3[0], y + p3[1]), (x + p4[0], y + p4[1])),
            fill=self.AIRCRAFT_COLOR, outline=self.AIRCRAFT_OUTLINE)
        self.draw.line((x + p1[0], y + p1[1], x + p5[0], y + p5[1]), fill=self.AIRCRAFT_OUTLINE, width=velocity_width)
        if height >= 0:
            t = "+" + str(abs(height))
        else:
            t = "-" + str(abs(height))
        if vspeed > 0:
            t = t + self.UP_CHARACTER
        if vspeed < 0:
            t = t + self.DOWN_CHARACTER
        w = self.draw.textlength(t, self.fonts[self.LARGE])
        if w + x + 4 * self.AIRCRAFT_SIZE - 2 > self.sizex:
            # would draw text outside, move to the left
            tposition = (x - 4 * self.AIRCRAFT_SIZE - w, int(y - self.LARGE / 2))
        else:
            tposition = (x + 4 * self.AIRCRAFT_SIZE + 1, int(y - self.LARGE / 2))
        self.draw.text(tposition, t, font=self.fonts[self.LARGE], fill=self.TEXT_COLOR)
        if tail is not None:
            self.draw.text((tposition[0], tposition[1] + self.LARGE), tail, font=self.fonts[self.VERYSMALL],
                           fill=self.TEXT_COLOR)

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
        self.draw.rectangle((0, 0, self.sizex - 1, self.sizey - 1), fill=self.BG_COLOR)  # clear everything in imagepass

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
        utc_color = utc_color or self.TEXT_COLOR
        timer_color = timer_color or self.TEXT_COLOR
        second_color = second_color or self.TEXT_COLOR

        self.draw.text((5, 0), "UTC", font=self.fonts[self.SMALL], fill=self.TEXT_COLOR)
        self.centered_text(self.SMALL, utctime, self.VERYLARGE, color=utc_color)
        if stoptime:
            self.draw.text((5, self.SMALL + self.VERYLARGE), "Timer", font=self.fonts[self.SMALL], fill=self.TEXT_COLOR)
            self.centered_text(2 * self.SMALL + self.VERYLARGE, stoptime, self.VERYLARGE, color=timer_color)

            if laptime:
                self.draw.text((5, 2 * self.SMALL + 2 * self.VERYLARGE), laptime_head, font=self.fonts[self.SMALL], fill=self.TEXT_COLOR)
                self.centered_text(3 * self.SMALL + 2 * self.VERYLARGE, laptime, self.VERYLARGE, color=second_color)
        self.bottom_line(left_text, middle_text, right_t)

    def meter(self, current, start_value, end_value, from_degree, to_degree, size, center_x, center_y,
              marks_distance, small_marks_distance, middle_text1, middle_text2, meter_color=None, text_color=None,
              middle_fontsize=0):
        meter_color = meter_color or self.TEXT_COLOR
        text_color = text_color or self.TEXT_COLOR
        middle_fontsize = middle_fontsize or self.SMALL

        big_mark_length = max(4, size // 16)
        small_mark_length = big_mark_length // 2
        arrow_line_size = size // 20
        arrow_head_size = arrow_line_size * 4
        arc_width = max(2, size // 64)
        center_size = (arrow_line_size * 3) // 4
        text_distance = small_mark_length
        arrow_distance = big_mark_length+small_mark_length
        text_offset_middle = size // 12

        # points of arrow at angle 0 (pointing up) for line drawing
        arrow = [
            (arrow_line_size // 2, 0),
            (-arrow_line_size // 2, 0),
            (-arrow_line_size // 2, -size // 2 + arrow_head_size),
            (0, -size // 2 + arrow_distance),
            (arrow_line_size // 2, -size // 2 + arrow_head_size),
            (arrow_line_size // 2, 0)
        ]
        deg_per_value = (to_degree - from_degree) / (end_value - start_value)
        # outside arc
        self.draw.arc(
            (center_x - size // 2, center_y - size // 2, center_x + size // 2, center_y + size // 2),
            from_degree - 90, to_degree - 90, width=arc_width, fill=meter_color
        )
        # small marks first
        line = (0, -size // 2), (0, -size // 2 + small_mark_length)
        m = start_value
        while m <= end_value:
            angle = deg_per_value * (m - start_value) + from_degree
            mark = translate(angle, line, (center_x, center_y))
            self.draw.line(mark, fill=meter_color, width=arc_width//2)
            m += small_marks_distance
        # large marks
        line = ((0, -size//2), (0, -size//2 + big_mark_length))
        m = start_value
        while m <= end_value:
            angle = deg_per_value * (m - start_value) + from_degree
            mark = translate(angle, line, (center_x, center_y))
            self.draw.line(mark, fill=meter_color, width=arc_width)
            # text
            marktext = str(m)
            tl = self.draw.textlength(marktext, self.fonts[self.LARGE])
            t_center = translate(angle, ((0, -size//2 + big_mark_length + self.LARGE//2 + text_distance),),
                                 (center_x, center_y))
            self.draw.text((t_center[0][0] - tl//2, t_center[0][1] - self.LARGE//2), marktext,
                      fill=meter_color, font=self.fonts[self.LARGE])
            m += marks_distance
        current = min(max(current, start_value), end_value) # limit to range
        angle = deg_per_value * (current - start_value) + from_degree
        ar = translate(angle, arrow, (center_x, center_y))
        self.draw.line(ar, fill=meter_color, width=arc_width)
        # centerpoint
        self.draw.ellipse((center_x - center_size, center_y - center_size, center_x + center_size, center_y + center_size),
                     fill=meter_color)

        if middle_text1 is not None:
            tl = self.draw.textlength(middle_text1, self.fonts[middle_fontsize])
            self.draw.text((center_x - tl//2, center_y - middle_fontsize - text_offset_middle), middle_text1,
                           font=self.fonts[middle_fontsize], fill=text_color, align="left")
        if middle_text2 is not None:
            tl = self.draw.textlength(middle_text2, self.fonts[middle_fontsize])
            self.draw.text((center_x - tl // 2, center_y + text_offset_middle), middle_text2,
                           font=self.fonts[middle_fontsize], fill=text_color, align="left")

    def compass(self, heading, error_message):
        czerox = self.sizex // 2
        czeroy = self.sizey // 2
        csize = self.sizey // 2  # radius of compass rose
        cmsize = self.sizey // 20 # size of compass marks
        line_width = 1 + min(self.sizex, self.sizey) // 64

        self.draw.ellipse((czerox - csize, 0, czerox + csize - 1, self.sizey - 1), outline=self.TEXT_COLOR,
                          fill=self.BG_COLOR, width=line_width)
        bw, bh = self.compass_aircraft.size
        if self.compass_aircraft.mode == "RGBA":
            self.image.paste(self.compass_aircraft, (czerox - bw // 2 + bw//32, czeroy - bh // 2))
            #  +bw//32 on x-axis, since image is not totally centered
        else:
            self.image.paste(self.TEXT_COLOR, (czerox - bw // 2 + bw//32, czeroy - bh //2), self.compass_aircraft)
            # +bw//32 on x-axis, since image is not totally centered
        self.draw.line((czerox, cmsize, czerox, czeroy - bh//2),
                       fill=self.TEXT_COLOR, width=line_width)     # -bw//2 on x-axis, since image is not totally centered

        self.bottom_line("", "", f"{heading}°")

        for m in range(0, 360, 10):
            s = math.sin(math.radians(m - heading + 90))
            c = math.cos(math.radians(m - heading + 90))
            x1, y1 = czerox - (csize - 1) * c, czeroy - (csize - 1) * s
            x2, y2 = czerox - (csize - cmsize) * c, czeroy - (csize - cmsize) * s
            width = line_width if m % 30 == 0 else line_width//2
            self.draw.line((x1, y1, x2, y2), fill=self.TEXT_COLOR, width=width)

            if m % 30 == 0:
                mark = {0: "N", 90: "E", 180: "S", 270: "W"}.get(m, str(m // 10))
                font = self.fonts[self.MORELARGE] if m % 90 == 0 else self.fonts[self.LARGE]
                color = self.HIGHLIGHT_COLOR if m % 90 == 0 else self.TEXT_COLOR
                tl = self.draw.textlength(mark, font)
                self.cdraw.rectangle((0, 0, self.LARGE * 2, self.LARGE * 2), fill="black")
                # in any case black, this is used as the rotation mask
                self.cdraw.text(((self.LARGE * 2 - tl) // 2, (self.LARGE * 2 - self.MORELARGE) // 2), mark,
                                font=font, fill="white")
                # "white" in any case, since the mask is binary, color is set later on with image.paste
                rotmask = self.mask.rotate(-m + heading, expand=False)
                center = (czerox - (csize - cmsize - self.LARGE // 2) * c,
                          czeroy - (csize - cmsize - self.LARGE // 2) * s)
                self.image.paste(color, (round(center[0] - self.LARGE),
                                                          round(center[1] - self.LARGE)), rotmask)

        if error_message:
            self.centered_text(120, error_message, self.LARGE)

    def vsi(self, vertical_speed, flight_level, gps_speed, gps_course, gps_altitude, vertical_max, vertical_min,
            error_message):
        pass

    def linepoints(self, pitch, roll, pitch_distance, length, scale):
        s = math.sin(math.radians(180 + roll))
        c = math.cos(math.radians(180 + roll))
        dist = (-pitch + pitch_distance) * scale
        move = (dist * s, dist * c)
        s1 = math.sin(math.radians(-90 - roll))
        c1 = math.cos(math.radians(-90 - roll))
        p1 = (self.ah_zerox - length * s1, self.ah_zeroy + length * c1)
        p2 = (self.ah_zerox + length * s1, self.ah_zeroy - length * c1)
        ps = (p1[0] + move[0], p1[1] + move[1])
        pe = (p2[0] + move[0], p2[1] + move[1])
        return ps, pe

    def rollmarks(self, roll, marks_width, marks_length):
        if self.ah_zerox > self.ah_zeroy:
            di = self.ah_zeroy
        else:
            di = self.ah_zerox

        for rm in self.ROLL_POSMARKS:
            s = math.sin(math.radians(rm - roll + 90))
            c = math.cos(math.radians(rm - roll + 90))
            if rm % 30 == 0:
                self.draw.line((self.ah_zerox - di * c, self.ah_zeroy - di * s, self.ah_zerox - (di - marks_length) * c,
                           self.ah_zeroy - (di - marks_length) * s), fill=self.AHRS_MARKS_COLOR, width=marks_width)
            else:
                self.draw.line((self.ah_zerox - di * c, self.ah_zeroy - di * s,
                    self.ah_zerox - (di - int(marks_length/2)) * c, self.ah_zeroy - (di - int(marks_length/2)) * s),
                    fill=self.AHRS_MARKS_COLOR, width=marks_width)
        # triangular pointer in the middle of the rollmarks
        self.draw.polygon((self.ah_zerox, marks_length+1, self.ah_zerox - int(marks_length/2), 1+int(marks_length*3/2),
                           self.ah_zerox + int(marks_length/2), 1+int(marks_length*3/2)), fill=self.AHRS_MARKS_COLOR)

    def slip(self, slipskid, centerline_width):
        slipsize_x = self.sizex//4   # slip indicator takes 1/2 of x-axis
        slipsize_y = self.sizey//24  # height of indicator (in both directions), also height of ball
        slipscale = slipsize_x//10
        slipskid = max(min(slipskid, 10), -10)
        # position slip at the bottom for 2/3 of x
        self.draw.rectangle((self.ah_zerox - slipsize_x, self.sizey-1 - slipsize_y*2,
                             self.ah_zerox + slipsize_x, self.sizey-1), fill="black")
        # now draw ball
        self.draw.ellipse((self.ah_zerox - slipskid * slipscale - slipsize_y, self.sizey-1 - slipsize_y*2,
                      self.ah_zerox - slipskid * slipscale + slipsize_y, self.sizey-1), fill="white")
        # middle line with background
        self.draw.line((self.ah_zerox, self.sizey-1 - slipsize_y * 2, self.ah_zerox, self.sizey-1),
                       fill="black", width=centerline_width*3)
        self.draw.line((self.ah_zerox, self.sizey-1 - slipsize_y * 2, self.ah_zerox, self.sizey-1),
                       fill="white", width=centerline_width)

    def earthfill(self, pitch, roll, length, scale):   # possible function for derived classed to implement fillings for earth
        # e.g. for epaper, this draws some type of black shading for the earth
        # for earthfill in range(0, -180, -3):
        #     self.draw.line((self.linepoints(pitch, roll, earthfill, max_length)), fill="black", width=1)
        # does not to be redefined if no filling is to be drawn
        pass

    def ahrs(self, pitch, roll, heading, slipskid, error_message):
        max_length = math.ceil(math.hypot(self.sizex, self.sizey))  # maximum line length for diagonal line
        line_width = max(1, self.sizey//60)  # the width of all lines (horizon, posmarks, rollmarks)
        pitchmark_length = self.sizey//6
        pitchscale = self.sizey / 6 / 10  # scaling factor for pitchmarks, so that +-20 is displayed
        rollmark_length = self.sizex//10
        line_width_middle = self.sizey//32  # middle right and left of pointer
        center_pointer_x = self.sizex//8
        center_pointer_y = self.sizey//16
        # this is the scaling factor for all drawings, 6 means: space for 6 pitch lines from -20, -10, 0, 10, 20

        h1, h2 = self.linepoints(pitch, roll, 0, max_length, pitchscale)  # horizon points
        h3, h4 = self.linepoints(pitch, roll, -180, max_length, pitchscale)
        self.draw.polygon((h1, h2, h4, h3), fill=self.AHRS_EARTH_COLOR)  # earth
        h3, h4 = self.linepoints(pitch, roll, 180, max_length, pitchscale)
        self.draw.polygon((h1, h2, h4, h3), fill=self.AHRS_SKY_COLOR)  # sky
        self.draw.line((h1, h2), fill=self.AHRS_HORIZON_COLOR, width=line_width)  # horizon line
        self.earthfill(pitch, roll, max_length, pitchscale)   # draw some special fillings for the earth
        for pm in self.PITCH_POSMARKS:  # pitchmarks
            self.draw.line((self.linepoints(pitch, roll, pm, pitchmark_length, pitchscale)), fill=self.AHRS_MARKS_COLOR,
                           width=line_width)
        # pointer in the middle
        self.draw.line((self.ah_zerox - 90, self.ah_zeroy, self.ah_zerox - 30, self.ah_zeroy),
                       width=line_width_middle, fill=self.TEXT_COLOR)
        self.draw.line((self.ah_zerox + 90, self.ah_zeroy, self.ah_zerox + 30, self.ah_zeroy),
                       width=line_width_middle, fill=self.TEXT_COLOR)
        self.draw.polygon((self.ah_zerox, self.ah_zeroy,
                           self.ah_zerox - center_pointer_x, self.ah_zeroy + center_pointer_y,
                           self.ah_zerox + center_pointer_x, self.ah_zeroy + center_pointer_y),
                          fill=self.AHRS_MARKS_COLOR)
        self.rollmarks(roll, line_width, rollmark_length)   # roll indicator
        self.slip(slipskid, line_width)     # slip indicator
        if error_message:
            self.centered_text( int(self.sizey/4), error_message, self.SMALL)
        self.bottom_line("Levl", "", "Zero")

    def text_screen(self, headline, subline, text, left_text, middle_text, r_text, offset=0):
        self.centered_text(0, headline, self.LARGE)
        txt_starty = self.LARGE
        if subline is not None:
            self.centered_text(txt_starty, subline, self.SMALL)
            txt_starty += self.SMALL
        txt_starty += self.SMALL//2   # some line indent
        self.draw.text((offset, txt_starty), text, font=self.fonts[self.SMALL])
        self.bottom_line(left_text, middle_text, r_text)

    def round_text(self, x, y, text, text_color=None, bg_color=None, yesno=True, out_color=None):
        # bg color is color of background, if none given, this is the normal background for this display
        # out_color is color of outline, if none given, outline is not displayed
        # if yesno is false, the text is crossed out
        bg_color = bg_color or self.BG_COLOR
        text_color = text_color or self.TEXT_COLOR
        tl = self.draw.textlength(text, self.fonts[self.VERYSMALL])
        self.draw.rounded_rectangle([x, y, x + tl + 4, y + self.VERYSMALL + 2], radius=4, fill=bg_color)
        if out_color:
            self.draw.rounded_rectangle([x, y, x + tl + 4, y + self.VERYSMALL + 2], radius=4, outline=out_color)
        self.draw.text((x + 2, y), text, font=self.fonts[self.VERYSMALL], fill=text_color)
        if not yesno:
            self.draw.line([x, y + self.VERYSMALL + 2, x + tl + self.VERYSMALL // 2, y], fill=text_color, width=2)
        return x + tl + self.VERYSMALL


    def screen_input(self, headline, subline, text, left, middle, right, prefix, inp, suffix):
        self.centered_text(0, headline, self.LARGE)
        txt_starty = self.LARGE
        if subline is not None:
            self.centered_text(txt_starty, subline, self.SMALL)
            txt_starty += self.LARGE
        bbox = self.draw.textbbox((0, txt_starty), text, font=self.fonts[self.SMALL])
        self.draw.text((0, txt_starty), text, font=self.fonts[self.SMALL], fill=self.TEXT_COLOR)
        bbox_p = self.draw.textbbox((bbox[0], bbox[3]), prefix, font=self.fonts[self.SMALL])
        self.draw.text((bbox[0], bbox[3]), prefix, fill=self.TEXT_COLOR, font=self.fonts[self.SMALL])
        bbox_rect = self.draw.textbbox((bbox_p[2], bbox[3]), inp, font=self.fonts[self.SMALL])
        self.draw.rectangle(bbox_rect, fill=self.TEXT_COLOR)
        self.draw.text((bbox_rect[0], bbox[3]), inp, font=self.fonts[self.SMALL], fill=self.BG_COLOR)
        self.draw.text((bbox_rect[2], bbox[3]), suffix, font=self.fonts[self.SMALL], fill=self.TEXT_COLOR)
        self.bottom_line(left, middle, right)

    def stratux(self, stat, altitude, gps_alt, gps_quality):
        pass

    def flighttime(self, last_flights, side_offset=0, long_version=False):
        # side offset is the space left on both sides, if there is enough space, the flight logs are centered
        headlines = (
            ("Date", "Start", "Dur", "Ldg"),
            ("Date", "Start", "Duration", "Landing"),
        )
        headline = headlines[1] if long_version else headlines[0]
        tab_space = (self.sizex - 2 * side_offset) // 4
        line_space = self.VERYSMALL // 3  # this gives a line indent
        starty = 0
        self.centered_text(starty, "Flight Logs ", self.SMALL)
        starty += self.SMALL + 2 * line_space
        self.draw.text((side_offset, starty), headline[0], font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)
        self.draw.text((side_offset + tab_space, starty), headline[1], font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)
        self.draw.text((side_offset + 2*tab_space, starty), headline[2], font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)
        self.draw.text((side_offset + 3*tab_space, starty), headline[3], font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)

        for f in last_flights:
            starty += self.VERYSMALL + line_space
            if starty >= self.sizey - self.VERYSMALL - 2*line_space:    # screen full
                break
            f[0] = f[0].replace(second=0, microsecond=0)
            date_string = f[0].strftime("%d.%m.%y" if long_version else "%d.%m.")
            self.draw.text((side_offset, starty), date_string, font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)
            self.draw.text((side_offset + tab_space, starty), f[0].strftime("%H:%M"), font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)
            if f[1] != 0:
                f[1] = f[1].replace(second=0, microsecond=0)
                delta = (f[1] - f[0]).total_seconds()
                self.draw.text((side_offset + 3*tab_space, starty), f[1].strftime("%H:%M"), font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)
            else:
                delta = (datetime.datetime.now(datetime.timezone.utc).replace(second=0, microsecond=0) - f[0]).total_seconds()
                state_string = "in the air" if long_version else "air"
                self.draw.text((side_offset + 3*tab_space, starty), state_string, font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)
            hours, remainder = divmod(delta, 3600)
            minutes, _ = divmod(remainder, 60)
            out = f' {int(hours):02}:{int(minutes):02} ' if long_version else f'{int(hours):02}:{int(minutes):02}'
            self.round_text(side_offset + 2*tab_space, starty, out, out_color=self.TEXT_COLOR)
        self.bottom_line("", "Mode", "Clear")

    def bar(self, y, text, val, max_val, bar_start, bar_end, color_table, unit="", valtext=None, minval=0,
            side_offset=0, line_offset=0, outline_offset=2):
        # color_table example for Epaper:
        #   color_table = {'outline': 'black', 'black_white_offset': 5}
        # color_table example for OLED:
        #   color_table = {'outline': 'white', 'green': 'green', 'yellow': 'DarkOrange', 'red': 'red',
        #                   'yellow_value': 22, 'red_value': 33}
        self.draw.text((side_offset, y), text, font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR, align="left")
        right_val = f"{int(max_val)}{unit}"
        self.right_text(y, right_val, self.VERYSMALL, offset=side_offset)

        if 'outline' in color_table:
            self.draw.rounded_rectangle([bar_start - outline_offset, y - outline_offset,
                        bar_end + outline_offset, y + self.VERYSMALL + outline_offset], radius=3,
                fill=None, outline=color_table['outline'], width=1)
        val = max(val, minval)
        xval = bar_start + (bar_end - bar_start) * val / max_val if max_val != 0 else bar_start
        t = valtext if valtext is not None else str(val)
        tl = self.draw.textlength(t, self.fonts[self.SMALL])

        if 'black_white_offset' in color_table and 'outline' in color_table:
            for b in range(bar_start, int(xval), color_table['black_white_offset']):
                self.draw.line([(b, y), (b, y + self.VERYSMALL)], fill=color_table['outline'], width=1)
        else:
            if 'red' in color_table and val >= color_table.get('red_value'):
                color = color_table.get('red')
            elif 'yellow' in color_table and val >= color_table.get('yellow_value'):
                color = color_table.get('yellow')
            else:
                color = color_table.get('green') if 'green' in color_table else self.TEXTCOLOR
            self.draw.rectangle([bar_start, y, xval, y + self.VERYSMALL], fill=color, outline=None)
        if 'outline' in color_table:
            self.draw.text(((bar_end - bar_start) // 2 + bar_start - tl // 2, y), t, font=self.fonts[self.VERYSMALL],
                           fill=color_table['outline'])
        return y + self.VERYSMALL + line_offset

    def cowarner(self, co_values, co_max, cr0, timeout, alarmlevel, alarmtext, simulation_mode=False):  # draw graph and co values
        pass

    def distance(self, now, gps_valid, gps_quality, gps_h_accuracy, distance_valid, gps_distance, gps_speed, baro_valid,
                 own_altitude, alt_diff, alt_diff_takeoff, vert_speed, ahrs_valid, ahrs_pitch, ahrs_roll,
                 ground_distance_valid, grounddistance, error_message):
        pass

    def distance_statistics(self, values, gps_valid, gps_altitude, dest_altitude, dest_alt_valid, ground_warnings):
        pass

    def gmeter(self, current, maxg, ming, error_message):
        pass

    def checklist_topic(self, ypos, topic, color=None, highlighted=False, toprint=True):
        color=color or self.TEXT_COLOR

        highlight_width = 1 + self.sizey // 200
        xpos = 2 * highlight_width + self.VERYSMALL // 4
        xpos_remark = xpos + self.VERYSMALL * 2
        xpos_sub = xpos + self.VERYSMALL
        topic_offset = 2 + self.sizey // 50
        subtopic_offset = self.sizey // 50
        remark_offset = self.sizey // 80
        topic_right_offset = self.VERYSMALL // 4 - highlight_width


        y = ypos
        if toprint:
            if topic.get('TASK'):
                self.draw.text((xpos, ypos), topic['TASK'], font=self.fonts[self.SMALL], fill=color)
            if topic.get('CHECK'):
                self.right_text(ypos, topic['CHECK'], self.SMALL, offset=topic_right_offset)
        y += self.SMALL

        if topic.get('REMARK'):
            y += remark_offset
            if toprint:
                self.draw.text((xpos_remark, y), topic['REMARK'], font=self.fonts[self.VERYSMALL], fill=color)
            y += self.VERYSMALL

        for i in range(1, 4):
            task_key = f'TASK{i}'
            check_key = f'CHECK{i}'
            if topic.get(task_key):
                y += subtopic_offset
                if toprint:
                    self.draw.text((xpos_sub, y), topic[task_key], font=self.fonts[self.SMALL], fill=color)
                if topic.get(check_key) and toprint:
                    self.right_text(y, topic[check_key], self.SMALL, offset=topic_right_offset)
                y += self.SMALL

        if highlighted and toprint:
            self.draw.rounded_rectangle([2+highlight_width, ypos - highlight_width,
                    self.sizex - highlight_width, y + 2 * highlight_width], width=highlight_width, radius=6,
                    outline=color)
        return y + topic_offset

    def checklist(self, checklist_name, checklist_items, current_index, last_list, color=None):
        color=color or self.TEXT_COLOR
        checklist_y = {'from': self.LARGE + self.LARGE // 2, 'to': self.sizey - self.VERYSMALL - self.VERYSMALL//2}
        global top_index

        self.centered_text(0, checklist_name, self.LARGE, color=color)
        if current_index == 0:
            top_index = 0  # new list, reset top index
        if current_index < top_index:
            top_index = current_index  # scroll up

        while True:  # check what would fit on the screen
            last_item = top_index
            size = self.checklist_topic(checklist_y['from'], checklist_items[last_item], highlighted=False, toprint=False)
            while last_item + 1 < len(checklist_items):
                last_item += 1
                size = self.checklist_topic(size, checklist_items[last_item], highlighted=False, toprint=False)
                if size > checklist_y['to']:  # last item did not fit
                    last_item -= 1
                    break

            # last item now shows the last one that fits
            if current_index + 1 <= last_item or last_item + 1 == len(checklist_items):
                break
            else:  # next item would not fit
                top_index += 1  # need to scroll, but now test again what would fit
                if current_index == len(checklist_items) - 1:  # list is finished
                    break

        # now display everything
        y = checklist_y['from']
        for item in range(top_index, last_item + 1):
            if item < len(checklist_items):
                y = self.checklist_topic(y, checklist_items[item], highlighted=(item == current_index), toprint=True)

        left = "PrevL" if current_index == 0 else "Prev"
        if last_list and current_index == len(checklist_items) - 1:  # last item
            self.bottom_line("Prev", "Mode", "StartL")
        elif last_list:
            self.bottom_line(left, "Mode", "Check")
        else:
            self.bottom_line(left, "NxtList", "Check")

    def shutdown(self, countdown, shutdownmode):
        messages = {
            0: "Shutdown all",
            1: "Shtdwn displ",
            2: "Reboot"
        }
        message = messages.get(shutdownmode, "Reboot")
        y = self.VERYSMALL
        y = self.centered_text(y, message, self.LARGE) + self.VERYSMALL//2
        y = self.centered_text(y, f"in {countdown} seconds!", self.LARGE) + self.VERYSMALL
        y = self.centered_text(y , "Left to cancel ...", self.SMALL) + self.VERYSMALL//2
        y = self.centered_text(y, "Middle display only ...",  self.SMALL)+ self.VERYSMALL//2
        self.centered_text(y, "Right for reboot all ...", self.SMALL)
        self.bottom_line("Canc", "Displ", "Rebo")


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

    def centered_text(self, y, text, fontsize, color=None):
        if color is None:
            color = self.TEXT_COLOR
        tl = self.draw.textlength(text, self.fonts[fontsize])
        self.draw.text((self.zerox - tl // 2, y), text, font=self.fonts[fontsize], fill=color)
        return y + fontsize

    def right_text(self, y, text, fontsize, color=None, offset=0):
        if color is None:
            color = self.TEXT_COLOR
        tl = self.draw.textlength(text, self.fonts[fontsize])
        self.draw.text((self.sizex - tl - offset, y), text, font=self.fonts[fontsize], fill=color)
        return y + fontsize


    def bottom_line(self, left, middle, right, color=None, offset_bottom=3, offset_left=3, offset_right=3):
        y = self.sizey - self.SMALL - offset_bottom
        color = color or self.TEXT_COLOR
        self.draw.text((offset_left, y), left, font=self.fonts[self.SMALL], fill=color)
        textlength = self.draw.textlength(right, self.fonts[self.SMALL])
        self.draw.text((self.sizex - textlength - offset_right, y), right,
                       font=self.fonts[self.SMALL], fill=color, align="right")
        self.centered_text(y, middle, self.SMALL, color)

    def graph(self, pos, size, data, minvalue, maxvalue, timeout, value_line1=None, value_line2=None,
            textcolor=None, graphcolor=None, linecolor=None, glinewidth=1, linewidth=1):
        x_val_space = self.VERYSMALL // 2   # space between value and graph
        x_val_linelength = self.VERYSMALL // 2  # length of value line
        y_offset = self.VERYSMALL // 4    # offset between x-axis and left corner of x-axis values
        textcolor = textcolor or self.TEXT_COLOR
        graphcolor = graphcolor or self.TEXT_COLOR
        linecolor = linecolor or self.TEXT_COLOR

        # Adjust zero lines to have room for text
        tl = self.draw.textlength(str(maxvalue), self.fonts[self.VERYSMALL])
        xpos = pos[0] + tl + x_val_space
        xsize = size[0] - tl - x_val_space
        ypos = pos[1] + self.VERYSMALL // 2
        ysize = size[1] - self.VERYSMALL

        def draw_value_line(value, y_off):
            ly = ypos + ysize - 1 - ysize * (value - minvalue) // (maxvalue - minvalue)
            ltl = self.draw.textlength(str(value), self.fonts[self.VERYSMALL])
            self.draw.text((xpos - ltl - x_val_space, ly - y_off), str(value),
                           font=self.fonts[self.VERYSMALL], fill=textcolor)
            return ly

        vlmin_y = ypos + ysize - 1
        atl = self.draw.textlength(str(minvalue), self.fonts[self.VERYSMALL])
        self.draw.text((xpos - atl - x_val_space, vlmin_y - self.VERYSMALL), str(minvalue),
                       font=self.fonts[self.VERYSMALL], fill=textcolor)
        vl1_y = draw_value_line(value_line1, self.VERYSMALL // 2)
        vl2_y = draw_value_line(value_line2, self.VERYSMALL // 2)
        vlmax_y = ypos
        self.draw.text((xpos - tl - x_val_space, vlmax_y - self.VERYSMALL//2), str(maxvalue),
                       font=self.fonts[self.VERYSMALL], fill=textcolor)
        # Draw outside text and frame
        self.draw.line([(xpos, ypos), (xpos+xsize-1, ypos), (xpos+xsize-1, ypos+ysize-1),
                        (xpos, ypos+ysize-1 ), (xpos, ypos)], width=linewidth)
        # Draw values below x-axis
        no_of_values = len(data)
        full_time = timeout * no_of_values
        timestr = time.strftime("%H:%M", time.gmtime())
        tl = self.draw.textlength(timestr, self.fonts[self.VERYSMALL])
        no_of_time = int(xsize // tl // 2 + 1)
        time_offset = full_time / no_of_time
        offset = (xsize - 1) // no_of_time
        x = xpos
        acttime = math.floor(time.time())
        # draw x-axis values
        for i in range(no_of_time + 1):
            self.draw.line((x, ypos + ysize - 1, x, ypos + ysize - 1 - x_val_linelength),
                           width=linewidth, fill=linecolor)
            timestr = time.strftime("%H:%M", time.gmtime(math.floor(acttime - (no_of_time - i) * time_offset)))
            self.draw.text((x - tl // 2, ypos + ysize - 1 + y_offset), timestr, font=self.fonts[self.VERYSMALL], fill=textcolor)
            x += offset

        # Draw graph lines
        lastpoint = None
        for i in range(0, len(data)):
            y = math.floor(ypos - 1 + ysize - ysize * (data[i] - minvalue) / (maxvalue - minvalue))
            y = max(min(y, ypos + ysize - 1), ypos)
            if i >= 1:  # we need at least two points before we draw
                x = math.floor(xpos + i * xsize / (len(data) - 1))
                self.draw.line([lastpoint, (x, y)], fill=graphcolor, width=glinewidth)
            else:
                x = xpos
            lastpoint = (x, y)

        # Draw dashed value lines
        def draw_dashed_line(ly):
            for lx in range(int(xpos), int(xpos + xsize), 6):
                self.draw.line([(lx, ly), (lx + 3, ly)], fill=linecolor, width=linewidth)

        draw_dashed_line(vl1_y)
        draw_dashed_line(vl2_y)

    def dashboard(self, x, y, dsizex, lines, color=None, bgcolor=None, rounding=False, headline=None,
                  headline_size=0):
        # dashboard, arguments are lines = ("text", "value"), ....
        # x and y are the starting points of the rounded rectangle
        # rounding triggers a box around the text with a headline of provided,
        # if rounding is not set, no headline is displayed
        color = color or self.TEXT_COLOR
        bgcolor = bgcolor or self.BG_COLOR
        if rounding:
            headline_size = headline_size or self.VERYSMALL
        indent = self.VERYSMALL // 2   # text indent on the left
        side_offset = 0   # offset right and left of the rounding
        line_indent = 0 # additional space between lines

        starty = y if not rounding else y + headline_size
        for line in lines:
            self.draw.text((x + indent + side_offset, starty + (self.SMALL - self.VERYSMALL) // 2), line[0],
                           font=self.fonts[self.VERYSMALL], fill=color,align="left")
            tl = self.draw.textlength(line[1], self.fonts[self.SMALL])
            self.draw.text((x + dsizex - side_offset - indent - tl, starty), line[1], font=self.fonts[self.SMALL], fill=color)
            starty += self.SMALL + line_indent
        if rounding:
            self.draw.rounded_rectangle([x + side_offset, y + headline_size//2, x + dsizex - side_offset,
                                         starty + headline_size//2 ], radius=6, fill=None, outline=color, width=2)
            if headline is not None:
                heading_indent = self.draw.textlength("---", self.fonts[headline_size])  # just 2 characters to the right
                heading_space = self.draw.textlength("-", self.fonts[headline_size])  # space in front and behind heading
                tl = self.draw.textlength(headline, self.fonts[headline_size])
                self.draw.rectangle([x + side_offset + heading_indent - heading_space, y,
                    x + heading_indent + tl + heading_space, y + headline_size], fill=bgcolor, outline=None)
                self.draw.text((x + side_offset + heading_indent, y), headline, font=self.fonts[headline_size], fill=color)
        return starty

