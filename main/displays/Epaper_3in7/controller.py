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
from PIL import Image, ImageDraw, ImageFont
import math
import time
import datetime
from pathlib import Path

# global constants
VERYLARGE = 48    # timer
MORELARGE = 36
LARGE = 30           # size of height indications of aircraft
SMALL = 24      # size of information indications on top and bottom
VERYSMALL = 18
AWESOME_FONTSIZE = 18   # bluetooth indicator
AIRCRAFT_SIZE = 6        # size of aircraft arrow
MINIMAL_CIRCLE = 20     # minimal size of mode-s circle
ARCPOSITION_EXCLUDE_FROM = 110
ARCPOSITION_EXCLUDE_TO = 250
# end definitions

# global device properties
sizex = 0
sizey = 0
zerox = 0
zeroy = 0
ah_zerox = 0  # zero point for ahrs
ah_zeroy = 0
max_pixel = 0
verylargefont = ""
morelargefont = ""
largefont = ""
smallfont = ""
verysmallfont = ""
awesomefont = ""
device = None
epaper_image = None
roll_posmarks = (-90, -60, -30, -20, -10, 0, 10, 20, 30, 60, 90)
pitch_posmarks = (-30, -20, -10, 10, 20, 30)
PITCH_SCALE = 4.0
msize = 15  # size of markings

# compass
compass_aircraft = None   # image of aircraft for compass-display
mask = None
cdraw = None
cmsize = 20        # length of compass marks
# co warner
space = 3  # space between scale figures and zero line
# end device globals


def posn(angle, arm_length):
    dx = round(math.cos(math.radians(270+angle)) * arm_length)
    dy = round(math.sin(math.radians(270+angle)) * arm_length)
    return dx, dy


def make_font(name, size):
    font_path = str(Path(__file__).resolve().parent.joinpath('fonts', name))
    return ImageFont.truetype(font_path, size)


def display():
    global device
    global epaper_image
    device.async_display_1Gray(device.getbuffer_optimized(epaper_image))


def is_busy():
    global device
    return device.async_is_busy()


def next_arcposition(old_arcposition):
    # defines next position of height indicator on circle. Can be used to exclude several ranges or
    # be used to define the next angle on the circle
    new_arcposition = (old_arcposition + 210) % 360
    if ARCPOSITION_EXCLUDE_TO >= new_arcposition >= ARCPOSITION_EXCLUDE_FROM:
        new_arcposition = (new_arcposition + 210) % 360
    return new_arcposition


def turn(sin_a, cos_a, p, zero):
    # help function which turns a point around zero with degree a, cos_a and sin_a in radians
    return round(zero[0] + p[0] * cos_a - p[1] * sin_a), round(zero[1] + p[0] * sin_a + p[1] * cos_a)


def translate(angle, points, zero):
    s = math.sin(math.radians(angle))
    c = math.cos(math.radians(angle))
    result = ()
    for p in points:
        result += (turn(s, c, p, zero),)
    return result


def init(fullcircle=False):
    global sizex
    global sizey
    global zerox
    global zeroy
    global ah_zerox
    global ah_zeroy
    global max_pixel
    global verylargefont
    global morelargefont
    global largefont
    global smallfont
    global verysmallfont
    global awesomefont
    global device
    global epaper_image
    global compass_aircraft
    global mask
    global cdraw

    device = epd3in7.EPD()
    device.init(0)
    device.Clear(0xFF, 0)   # necessary to overwrite everything
    epaper_image = Image.new('1', (device.height, device.width), 0xFF)
    draw = ImageDraw.Draw(epaper_image)
    device.init(1)
    device.Clear(0xFF, 1)
    sizex = device.height
    sizey = device.width
    zerox = sizex / 2
    if not fullcircle:
        zeroy = 200    # not centered
        max_pixel = 400
    else:
        zeroy = sizey / 2
        max_pixel = sizey
    ah_zeroy = sizey / 2   # zero line for ahrs
    ah_zerox = sizex / 2
    verylargefont = make_font("Font.ttc", VERYLARGE)
    morelargefont = make_font("Font.ttc", MORELARGE)
    largefont = make_font("Font.ttc", LARGE)               # font for height indications
    smallfont = make_font("Font.ttc", SMALL)            # font for information indications
    verysmallfont = make_font("Font.ttc", VERYSMALL)  # font for information indications
    awesomefont = make_font("fontawesome-webfont.ttf", AWESOME_FONTSIZE)  # for bluetooth indicator
    # measure time for refresh
    start = time.time()
    # do sync version of display to measure time
    device.display_1Gray(device.getbuffer_optimized(epaper_image))
    end = time.time()
    display_refresh = end-start
    # compass
    pic_path = str(Path(__file__).resolve().parent.joinpath('plane-white-128x128.bmp'))
    compass_aircraft = Image.open(pic_path)
    mask = Image.new('1', (LARGE * 2, LARGE * 2))
    cdraw = ImageDraw.Draw(mask)
    return draw, max_pixel, zerox, zeroy, display_refresh


def cleanup():
    global device

    device.init(0)
    device.Clear(0xFF, 0)
    device.sleep()
    device.Dev_exit()


def refresh():
    global device

    device.Clear(0xFF, 0)  # necessary to overwrite everything
    device.init(1)


def clear(draw):
    draw.rectangle((0, 0, sizex - 1, sizey - 1), fill="white")  # clear everything in image


def centered_text(draw, y, text, font, fill):
    tl = draw.textlength(text, font)
    draw.text((zerox - tl / 2, y), text, font=font, fill=fill)


def right_text(draw, y, text, font, fill, offset=0):
    tl = draw.textlength(text, font)
    draw.text((sizex-5-tl-offset, y), text, font=font, fill=fill)


def bottom_line(draw, left, middle, right):
    draw.text((5, sizey - SMALL - 3), left, font=smallfont, fill="black")
    textlength = draw.textlength(right, smallfont)
    draw.text((sizex - textlength - 8, sizey - SMALL - 3), right, font=smallfont, fill="black", align="right")
    centered_text(draw, sizey - SMALL - 3, middle, smallfont, fill="black")


def startup(draw, version, target_ip, seconds):
    logopath = str(Path(__file__).resolve().parent.joinpath('stratux-logo-192x192.bmp'))
    logo = Image.open(logopath)
    draw.bitmap((zerox-192/2, 0), logo, fill="black")
    versionstr = "Radar " + version
    centered_text(draw, 188, versionstr, largefont, fill="black")
    centered_text(draw, sizey - 2 * VERYSMALL - 2, "Connecting to " + target_ip, verysmallfont, fill="black")
    display()
    time.sleep(seconds)


def aircraft(draw, x, y, direction, height, vspeed, nspeed_length, tail):
    p1 = posn(direction, 2 * AIRCRAFT_SIZE)
    p2 = posn(direction + 150, 4 * AIRCRAFT_SIZE)
    p3 = posn(direction + 180, 2 * AIRCRAFT_SIZE)
    p4 = posn(direction + 210, 4 * AIRCRAFT_SIZE)
    p5 = posn(direction, nspeed_length)  # line for speed

    draw.polygon(((x + p1[0], y + p1[1]), (x + p2[0], y + p2[1]), (x + p3[0], y + p3[1]), (x + p4[0], y + p4[1])),
                 fill="black", outline="black")
    draw.line((x + p1[0], y + p1[1], x + p5[0], y + p5[1]), fill="black", width=3)
    if height >= 0:
        t = "+" + str(abs(height))
    else:
        t = "-" + str(abs(height))
    if vspeed > 0:
        t = t + '\u2197'
    if vspeed < 0:
        t = t + '\u2198'
    w = draw.textlength(t, largefont)
    if w + x + 4 * AIRCRAFT_SIZE - 2 > sizex:
        # would draw text outside, move to the left
        tposition = (x - 4 * AIRCRAFT_SIZE - w, int(y - LARGE/2))
    else:
        tposition = (x + 4 * AIRCRAFT_SIZE + 1, int(y - LARGE/2))
    draw.text(tposition, t, font=largefont, fill="black")
    if tail is not None:
        draw.text((tposition[0], tposition[1] + LARGE), tail, font=verysmallfont, fill="black")


def modesaircraft(draw, radius, height, arcposition, vspeed, tail):
    if radius < MINIMAL_CIRCLE:
        radius = MINIMAL_CIRCLE
    draw.ellipse((zerox-radius, zeroy-radius, zerox+radius, zeroy+radius), width=3, outline="black")
    arctext = posn(arcposition, radius)
    if height > 0:
        signchar = "+"
    else:
        signchar = "-"
    t = signchar+str(abs(height))
    if vspeed > 0:
        t = t + '\u2197'
    if vspeed < 0:
        t = t + '\u2198'
    w = draw.textlength(t, largefont)
    tposition = (zerox+arctext[0]-w/2, zeroy+arctext[1]-LARGE/2)
    draw.rectangle((tposition, (tposition[0]+w, tposition[1]+LARGE+2)), fill="white")
    draw.text(tposition, t, font=largefont, fill="black")
    if tail is not None:
        tl = draw.textlength(tail, verysmallfont)
        draw.rectangle((tposition[0], tposition[1] + LARGE, tposition[0] + tl,
                        tposition[1] + LARGE + VERYSMALL), fill="white")
        draw.text((tposition[0], tposition[1] + LARGE), tail, font=verysmallfont, fill="black")


def situation(draw, connected, gpsconnected, ownalt, course, range, altdifference, bt_devices, sound_active,
              gps_quality, gps_h_accuracy, optical_bar, basemode, extsound, co_alarmlevel, co_alarmstring):
    draw.ellipse((zerox-max_pixel/2, zeroy-max_pixel/2, zerox+max_pixel/2, zeroy+max_pixel/2), outline="black")
    draw.ellipse((zerox-max_pixel/4, zeroy-max_pixel/4, zerox+max_pixel/4, zeroy+max_pixel/4), outline="black")
    draw.ellipse((zerox-2, zeroy-2, zerox+2, zeroy+2), outline="black")

    draw.text((5, 1), str(range)+" nm", font=smallfont, fill="black")

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
    draw.text((5, SMALL+10), t, font=verysmallfont, fill="black")

    t = "FL"+str(round(ownalt / 100))
    textlength = draw.textlength(t, verysmallfont)
    draw.text((sizex - textlength - 5, SMALL+10), t, font=verysmallfont, fill="black")

    t = str(altdifference) + " ft"
    textlength = draw.textlength(t, smallfont)
    draw.text((sizex - textlength - 5, 1), t, font=smallfont, fill="black", align="right")

    text = str(course) + '°'
    centered_text(draw, 1, text, smallfont, fill="black")

    if not gpsconnected:
        centered_text(draw, 70, "No GPS", smallfont, fill="black")
    if not connected:
        centered_text(draw, 30, "No Connection!", smallfont, fill="black")
    if co_alarmlevel > 0:
        centered_text(draw, 250, "CO Alarm: " + co_alarmstring, smallfont, fill="black")

    if extsound or bt_devices > 0:
        if sound_active:
            t = ""
            if extsound:
                t += "\uf028"  # volume symbol
            if bt_devices > 0:
                t += "\uf293"  # bluetooth symbol
        else:
            t = "\uf1f6"  # bell off symbol
        textlength = draw.textlength(t, awesomefont)
        draw.text((sizex - textlength - 5, sizey - SMALL), t, font=awesomefont, fill="black")

    # optical keep alive bar at right side
    draw.line((sizex-8, 80+optical_bar*10, sizex-8, 80+optical_bar*10+8), fill="black", width=5)


def timer(draw, utctime, stoptime, laptime, laptime_head, left_text, middle_text, right_t, timer_runs):
    draw.text((5, 0), "UTC", font=smallfont, fill="black")
    centered_text(draw, SMALL, utctime, verylargefont, fill="black")
    if stoptime is not None:
        draw.text((5, SMALL+VERYLARGE), "Timer", font=smallfont, fill="black")
        centered_text(draw, 2*SMALL+VERYLARGE, stoptime, verylargefont, fill="black")
        if laptime is not None:
            draw.text((5, 2*SMALL + 2 * VERYLARGE), laptime_head, font=smallfont, fill="black")
            centered_text(draw, 3*SMALL+2*VERYLARGE, laptime, verylargefont, fill="black")

    draw.text((5, sizey-SMALL-3), left_text, font=smallfont, fill="black")
    textlength = draw.textlength(right_t, smallfont)
    draw.text((sizex-textlength-8, sizey-SMALL-3), right_t, font=smallfont, fill="black", align="right")
    centered_text(draw, sizey-SMALL-3, middle_text, smallfont, fill="black")


def meter(draw, current, start_value, end_value, from_degree, to_degree, size, center_x, center_y,
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
    # large marks
    line = ((0, -size/2+1), (0, -size/2+big_mark_length))
    m = start_value
    while m <= end_value:
        angle = deg_per_value*(m-start_value) + from_degree
        mark = translate(angle, line, (center_x, center_y))
        draw.line(mark, fill="black", width=4)
        # text
        marktext = str(m)
        tl = draw.textlength(marktext, largefont)
        t_center = translate(angle, ((0, -size/2 + big_mark_length + LARGE/2 + text_distance), ), (center_x, center_y))
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
        tl = draw.textlength(middle_text1, smallfont)
        draw.text((center_x - tl/2, center_y - SMALL - 20), middle_text1, font=smallfont, fill="black", align="left")
    if middle_text2 is not None:
        tl = draw.textlength(middle_text2, smallfont)
        draw.text((center_x-tl/2, center_y+20), middle_text2, font=smallfont, fill="black", align="left")


def gmeter(draw, current, maxg, ming, error_message):
    gm_size = 280
    meter(draw, current, -3, 5, 110, 430, gm_size, 140, 140, 1, 0.25, "G-Force", None)

    right_center_x = (sizex-gm_size)/2+gm_size    # center of remaining part
    t = "G-Meter"
    tl = draw.textlength(t, largefont)
    draw.text((right_center_x - tl / 2, 30), t, font=largefont, fill="black", align="left")
    draw.text((gm_size+30, 98), "max", font=smallfont, fill="black")
    right_text(draw, 95, "{:+1.2f}".format(maxg), largefont, fill="black")
    if error_message is None:
        draw.text((gm_size+30, 138), "act", font=smallfont, fill="black")
        right_text(draw, 135, "{:+1.2f}".format(current), largefont, fill="black")
    else:
        draw.text((gm_size+30, 138), error_message, font=largefont, fill="black")
    draw.text((gm_size+30, 178), "min", font=smallfont, fill="black")
    right_text(draw, 175, "{:+1.2f}".format(ming), largefont, fill="black")

    right = "Reset"
    middle = "    Mode"
    textlength = draw.textlength(right, smallfont)
    draw.text((sizex-textlength-8, sizey-SMALL-3), right, font=smallfont, fill="black", align="right")
    centered_text(draw, sizey-SMALL-3, middle, smallfont, fill="black")


def compass(draw, heading, error_message):
    global epaper_image
    global mask
    global cdraw

    czerox = sizex / 2
    czeroy = sizey / 2
    csize = sizey / 2  # radius of compass rose

    draw.ellipse((sizex/2-csize, 0, sizex/2+csize-1, sizey - 1), outline="black", fill="white", width=4)
    draw.bitmap((zerox - 60, 70), compass_aircraft, fill="black")
    draw.line((czerox, 20, czerox, 70), fill="black", width=4)
    text = str(heading) + '°'
    tl = draw.textlength(text, smallfont)
    draw.text((sizex - tl - 100, sizey - SMALL - 10), text, font=smallfont, fill="black", align="right")
    for m in range(0, 360, 10):
        s = math.sin(math.radians(m - heading + 90))
        c = math.cos(math.radians(m - heading + 90))
        if m % 30 != 0:
            draw.line((czerox - (csize - 1) * c, czeroy - (csize - 1) * s, czerox - (csize - cmsize) * c,
                       czeroy - (csize - cmsize) * s), fill="black", width=2)
        else:
            draw.line((czerox - (csize - 1) * c, czeroy - (csize - 1) * s, czerox - (csize - cmsize) * c,
                       czeroy - (csize - cmsize) * s), fill="black", width=4)
            cdraw.rectangle((0, 0, LARGE * 2, LARGE * 2), fill="black")
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
                tl = draw.textlength(mark, largefont)
                cdraw.text(((LARGE * 2 - tl) / 2, LARGE / 2), mark, 1, font=largefont)
            else:
                tl = draw.textlength(mark, morelargefont)
                cdraw.text(((LARGE * 2 - tl) / 2, (LARGE * 2 - MORELARGE) / 2), mark, 1, font=morelargefont)
            rotmask = mask.rotate(-m + heading, expand=False)
            center = (czerox - (csize - cmsize - LARGE / 2) * c, czeroy - (csize - cmsize - LARGE / 2) * s)
            epaper_image.paste("black", (round(center[0] - LARGE), round(center[1] - LARGE)), rotmask)
    if error_message is not None:
        centered_text(draw, 120, error_message, largefont, fill="black")


def vsi(draw, vertical_speed, flight_level, gps_speed, gps_course, gps_altitude, vertical_max, vertical_min,
        error_message):
    meter(draw, vertical_speed/100, -20, 20, 110, 430, sizey, sizey/2, sizey/2, 5, 1, None, None)
    draw.text((35, sizey/2 - VERYSMALL - 25), "up", font=verysmallfont, fill="black", align="left")
    draw.text((35, sizey/2 + 25), "dn", font=verysmallfont, fill="black", align="left")
    middle_text = "Vertical Speed"
    tl = draw.textlength(middle_text, verysmallfont)
    draw.text((sizey/2 - tl / 2, sizey/2 - VERYSMALL - 10), middle_text, font=verysmallfont, fill="black", align="left")
    middle_text = "100 feet per min"
    tl = draw.textlength(middle_text, verysmallfont)
    draw.text((sizey/2 - tl / 2, sizey/2 + 10), middle_text, font=verysmallfont, fill="black", align="left")

    # right data display
    draw.text((300, 10), "Vert Speed [ft/min]", font=verysmallfont, fill="black", align="left")
    draw.text((330, 31), "act", font=verysmallfont, fill="black", align="left")
    draw.text((330, 55), "max", font=verysmallfont, fill="black", align="left")
    draw.text((330, 79), "min", font=verysmallfont, fill="black", align="left")
    right_text(draw, 28, "{:+1.0f}".format(vertical_speed), smallfont, fill="black")
    right_text(draw, 52, "{:+1.0f}".format(vertical_max), smallfont, fill="black")
    right_text(draw, 76, "{:+1.0f}".format(vertical_min), smallfont, fill="black")
    draw.text((300, 163), "Flight-Level", font=verysmallfont, fill="black", align="left")
    right_text(draw, 160, "{:1.0f}".format(round(flight_level/100)), smallfont, fill="black")
    draw.text((300, 187), "GPS-Alt [ft]", font=verysmallfont, fill="black", align="left")
    right_text(draw, 184, "{:1.0f}".format(gps_altitude), smallfont, fill="black")
    draw.text((300, 211), "GpsSpd [kts]", font=verysmallfont, fill="black", align="left")
    right_text(draw, 208, "{:1.1f}".format(gps_speed), smallfont, fill="black")

    if error_message is not None:
        centered_text(draw, 60, error_message, verylargefont, fill="black")

    right = "Reset"
    middle = "    Mode"
    textlength = draw.textlength(right, smallfont)
    draw.text((sizex - textlength - 8, sizey - SMALL - 3), right, font=smallfont, fill="black", align="right")
    centered_text(draw, sizey - SMALL - 3, middle, smallfont, fill="black")


def shutdown(draw, countdown, shutdownmode):
    if shutdownmode == 0:   # shutdown stratux + display
        message = "Shutdown stratux & display"
    elif shutdownmode == 1:
        message = "Shutdown display"
    else:
        message = "Reboot"
    centered_text(draw, 10, message, largefont, fill="black")
    message = "in " + str(countdown) + " seconds!"
    centered_text(draw, 40, message, largefont, fill="black")
    message = "Press left button to cancel ..."
    centered_text(draw, 110, message, smallfont, fill="black")
    message = "Press middle for display only ..."
    centered_text(draw, 140, message, smallfont, fill="black")
    message = "Press right for reboot all ..."
    centered_text(draw, 170, message, smallfont, fill="black")

    left_text = "Cancel"
    middle_text = "Display only"
    right_text = "Reboot"
    draw.text((5, sizey - SMALL - 3), left_text, font=smallfont, fill="black")
    textlength = draw.textlength(right_text, smallfont)
    draw.text((sizex - textlength - 8, sizey - SMALL - 3), right_text, font=smallfont, fill="black", align="right")
    centered_text(draw, sizey - SMALL - 3, middle_text, smallfont, fill="black")


def rollmarks(draw, roll):
    if ah_zerox > ah_zeroy:
        di = ah_zeroy
    else:
        di = ah_zerox

    for rm in roll_posmarks:
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


def slip(draw, slipskid):
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


def ahrs(draw, pitch, roll, heading, slipskid, error_message):
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

    for pm in pitch_posmarks:  # pitchmarks
        draw.line((linepoints(pitch, roll, pm, 30)), fill="black", width=4)

    # pointer in the middle
    draw.line((ah_zerox - 90, ah_zeroy, ah_zerox - 30, ah_zeroy), width=6, fill="black")
    draw.line((ah_zerox + 90, ah_zeroy, ah_zerox + 30, ah_zeroy), width=6, fill="black")
    draw.polygon((ah_zerox, ah_zeroy + 4, ah_zerox - 20, ah_zeroy + 16, ah_zerox + 20, ah_zeroy + 16),
                 fill="black")

    # roll indicator
    rollmarks(draw, roll)
    # slip indicator
    slip(draw, slipskid)

    # infotext = "P:" + str(pitch) + " R:" + str(roll)
    if error_message:
        centered_text(draw, 80, error_message, smallfont, fill="black")


def text_screen(draw, headline, subline, text, left_text, middle_text, right_text):
    centered_text(draw, 0, headline, verylargefont, fill="black")
    txt_starty = VERYLARGE
    if subline is not None:
        centered_text(draw, txt_starty, subline, largefont, fill="black")
        txt_starty += LARGE
    draw.text((5, txt_starty), text, font=smallfont, fill="black")

    draw.text((5, sizey - SMALL - 3), left_text, font=smallfont, fill="black")
    textlength = draw.textlength(right_text, smallfont)
    draw.text((sizex - textlength - 8, sizey - SMALL - 3), right_text, font=smallfont, fill="black", align="right")
    centered_text(draw, sizey - SMALL - 3, middle_text, smallfont, fill="black")


def screen_input(draw, headline, subline, text, left, middle, right, prefix, inp, suffix):
    centered_text(draw, 0, headline, largefont, fill="black")
    txt_starty = LARGE
    if subline is not None:
        centered_text(draw, LARGE, subline, smallfont, fill="black")
        txt_starty += LARGE
    bbox = draw.textbbox((0, txt_starty), text, font=smallfont)
    draw.text((0, txt_starty), text, font=smallfont, fill="black")
    bbox_p = draw.textbbox((bbox[0], bbox[3]), prefix, font=smallfont)
    draw.text((bbox[0], bbox[3]), prefix, fill="black", font=smallfont)
    bbox_rect = draw.textbbox((bbox_p[2], bbox[3]), inp, font=smallfont)
    draw.rectangle(bbox_rect, fill="black")
    draw.text((bbox_rect[0], bbox[3]), inp, font=smallfont, fill="white")
    draw.text((bbox_rect[2], bbox[3]), suffix, font=smallfont, fill="black")

    draw.text((5, sizey - SMALL - 3), left, font=smallfont, fill="black")
    textlength = draw.textlength(right, smallfont)
    draw.text((sizex - textlength - 8, sizey - SMALL - 3), right, font=smallfont, fill="black", align="right")
    centered_text(draw, sizey - SMALL - 8, middle, smallfont, fill="black")


def bar(draw, y, text, val, max_val, yellow, red, unit="", valtext=None, minval=0):
    bar_start = 100
    bar_end = 420

    draw.text((5, y), text, font=verysmallfont, fill="black", align="left")
    right_val = str(int(max_val)) + unit
    textlength = draw.textlength(right_val, verysmallfont)
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
    tl = draw.textlength(t, verysmallfont)
    draw.text(((bar_end-bar_start)/2+bar_start-tl/2, y), t, font=verysmallfont, fill="black",
              stroke_width=1, stroke_fill="white")
    return y+VERYSMALL+12


def round_text(draw, x, y, text, color, yesno=True, out=None):
    tl = draw.textlength(text, verysmallfont)
    draw.rounded_rectangle([x, y, x+tl+10, y+VERYSMALL+2], radius=4, fill=color, outline=out)
    draw.text((x+5, y), text, font=verysmallfont, fill="black")
    if not yesno:
        draw.line([x, y+VERYSMALL+2, x+tl+10, y], fill="black", width=2)
    return x+tl+20


def stratux(draw, stat, altitude, gps_alt, gps_quality):
    starty = 0
    centered_text(draw, 0, "Stratux " + stat['version'], smallfont, fill="black")
    starty += SMALL+8
    starty = bar(draw, starty, "1090", stat['ES_messages_last_minute'], stat['ES_messages_max'], 0, 0)
    if stat['OGN_connected']:
        starty = bar(draw, starty, "OGN", stat['OGN_messages_last_minute'], stat['OGN_messages_max'], 0, 0)
        noise_text = str(round(stat['OGN_noise_db'], 1)) + "@" + str(round(stat['OGN_gain_db'], 1)) + "dB"
        starty = bar(draw, starty, "noise", stat['OGN_noise_db'], 25, 12, 18, unit="dB", minval=1, valtext=noise_text)
    if stat['UATRadio_connected']:
        starty = bar(draw, starty, "UAT", stat['UAT_messages_last_minute'], stat['UAT_messages_max'], 0, 0)
    starty += 6
    if stat['CPUTemp'] > -300:    # -300 means no value available
        starty = bar(draw, starty, "temp", round(stat['CPUTemp'], 1), round(stat['CPUTempMax'], 0), 70, 80, "°C")
        starty += 3
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
    draw.text((240, starty), t, font=verysmallfont, fill="black")

    starty += VERYSMALL+5

    draw.text((5, starty), "altitudes", font=verysmallfont, fill="black")
    if stat['GPS_position_accuracy'] < 19999:
        alt = '{:5.0f}'.format(gps_alt)
    else:
        alt = " --- "
    t = "FL" + str(round(altitude/100))
    draw.text((100, starty), t, font=verysmallfont, fill="black")
    t = "GPS-Alt " + alt + " ft"
    draw.text((240, starty), t, font=verysmallfont, fill="black")
    starty += VERYSMALL + 10
    draw.text((5, starty), "sensors", font=verysmallfont, fill="black")
    x = round_text(draw, 100, starty, "IMU", "white", stat['IMUConnected'], out="black")
    round_text(draw, x, starty, "BMP", "white", stat['BMPConnected'], out="black")


def flighttime(draw, last_flights):
    starty = 0
    centered_text(draw, 0, "Flight Logs ", smallfont, fill="black")
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
        round_text(draw, 220, starty, out, "white", out="black")
        starty += VERYSMALL + 5
        maxlines -= 1
        if maxlines <= 0:
            break


def graph(draw, xpos, ypos, xsize, ysize, data, minvalue, maxvalue, value_line1, value_line2, timeout):
    tl = math.floor(draw.textlength(str(maxvalue), verysmallfont))    # for adjusting x and y
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
    vl2_y = math.floor(ypos + ysize - ysize * (value_line2 - minvalue) / (maxvalue - minvalue))
    tl = draw.textlength(str(value_line2), verysmallfont)
    draw.text((xpos - tl - space, vl2_y - VERYSMALL/2), str(value_line2), font=verysmallfont, fill="black")

    vlmax_y = ypos
    tl = draw.textlength(str(maxvalue), verysmallfont)
    draw.text((xpos - tl - space, vlmax_y - VERYSMALL/2), str(maxvalue), font=verysmallfont, fill="black")

    draw.rectangle((xpos, ypos, xpos+xsize, ypos+ysize), outline="black", width=3, fill="white")

    # values below x-axis
    no_of_values = len(data)
    full_time = timeout * no_of_values   # time for full display in secs
    timestr = time.strftime("%H:%M", time.gmtime())
    tl = draw.textlength(timestr, verysmallfont)
    no_of_time = math.floor(xsize / tl / 2) + 1  # calculate maximum number of time indications
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
        y = ypos-4 + ysize - ysize * (data[i] - minvalue) / (maxvalue - minvalue)
        if y < ypos:
            y = ypos   # if value is outside
        if y > ypos+ysize-1:
            x = ypos+ysize-1
        if i >= 1:  # we need at least two points before we draw
            x = xpos + i * xsize / (len(data)-1)
            draw.line([lastpoint, (x, y)], fill="black", width=3)
        else:
            x = xpos
        lastpoint = (x, y)
    # value_line 1
    y = ypos + ysize - ysize * (value_line1 - minvalue) / (maxvalue - minvalue)
    for x in range(xpos, xpos+xsize, 6):
        draw.line([(x, y), (x + 3, y)], fill="black", width=1)
    # value_line 2
    y = ypos + ysize - ysize * (value_line2 - minvalue) / (maxvalue - minvalue)
    for x in range(xpos, xpos+xsize, 6):
        draw.line([(x, y), (x + 3, y)], fill="black", width=1)


def cowarner(draw, co_values, co_max, r0, timeout, alarmlevel, alarmppm, alarmperiod):   # draw graph and co values
    if alarmlevel == 0:
        centered_text(draw, 0, "CO Warner: No CO alarm", largefont, fill="black")
    else:
        if alarmperiod > 60:
            alarmstr = "CO: {:d} ppm longer {:d} min".format(alarmppm, math.floor(alarmperiod/60))
        else:
            alarmstr = "CO: {:d} ppm longer {:d} sec".format(alarmppm, math.floor(alarmperiod))
        centered_text(draw, 0, alarmstr, largefont, fill="black")
    graph(draw, 0, 40, 300, 200, co_values, 0, 120, 50, 100, timeout)
    draw.text((320, 50 + SMALL - VERYSMALL), "Warnlevel:", font=verysmallfont, fill="black")
    right_text(draw, 50, "{:3d}".format(alarmlevel), smallfont, fill="black")

    if len(co_values) > 0:
        draw.text((320, 120+SMALL-VERYSMALL), "CO act:", font=verysmallfont, fill="black")
        right_text(draw, 120, "{:3d}".format(co_values[len(co_values) - 1]), smallfont, fill="black")
    draw.text((320, 140+SMALL-VERYSMALL), "CO max:", font=verysmallfont, fill="black")
    right_text(draw, 140, "{:3d}".format(co_max), smallfont, fill="black")
    draw.text((320, 196), "R0:", font=verysmallfont, fill="black")
    right_text(draw, 196, "{:.1f}k".format(r0/1000), verysmallfont, fill="black")

    draw.text((8, sizey - SMALL - 3), "Calibrate", font=smallfont, fill="black", align="left")
    right = "Reset"
    textlength = draw.textlength(right, smallfont)
    draw.text((sizex - textlength - 8, sizey - SMALL - 3), right, font=smallfont, fill="black", align="right")
    centered_text(draw, sizey - SMALL - 3, "Mode", smallfont, fill="black")


def data_item(draw, leftx, y, rightx, text, value):
    draw.text((leftx, y + (SMALL-VERYSMALL) / 2), text, font=verysmallfont, fill="black", align="left")
    tl = draw.textlength(value, smallfont)
    draw.text((rightx - tl, y), value, font=smallfont, fill="black")


def dashboard(draw, x, y, dsizex, rounding, headline, lines):
    # dashboard, arguments are lines = ("text", "value"), ....
    starty = y + VERYSMALL/2
    for line in lines:
        draw.text((x + 7, starty + (SMALL - VERYSMALL) / 2), line[0], font=verysmallfont, fill="black", align="left")
        tl = draw.textlength(line[1], smallfont)
        draw.text((x + dsizex - 7 - tl, starty), line[1], font=smallfont, fill="black")
        starty += SMALL + 3
    if rounding:
        starty += VERYSMALL/2
        draw.rounded_rectangle([x, y, x + dsizex, starty], radius=6, fill=None, outline="black", width=2)
        tl = draw.textlength(headline, verysmallfont)
        draw.rectangle([x + 20, y - SMALL/2, x + 20 + tl + 8, y + SMALL/2], fill="white", outline=None)
    draw.text((x+20+4, y - VERYSMALL/2), headline, font=verysmallfont, fill="black")
    return starty


def distance(draw, now, gps_valid, gps_quality, gps_h_accuracy, distance_valid, gps_distance, gps_speed, baro_valid,
             own_altitude, alt_diff, alt_diff_takeoff, vert_speed, ahrs_valid, ahrs_pitch, ahrs_roll,
             ground_distance_valid, grounddistance, error_message):

    centered_text(draw, 0, "GPS Distance", smallfont, fill="black")

    lines = (
        ("Date", "{:0>2d}.{:0>2d}.{:0>4d}".format(now.day, now.month, now.year)),
        ("UTC", "{:0>2d}:{:0>2d}:{:0>2d},{:1d}".format(now.hour, now.minute, now.second,
                                                       math.floor(now.microsecond/100000)))
    )
    starty = dashboard(draw, 5, 35, 225, True, "Date/Time", lines)

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
    starty = dashboard(draw, 5, starty, 225, True, "GPS", lines)
    if ground_distance_valid:
        lines = (
            ("Grd Dist [cm]", "{:+3.1f}".format(grounddistance/10)),
        )
        dashboard(draw, 5, starty, 225, True, "Ground Sensor", lines)

    if ahrs_valid:
        lines = (
            ("Pitch [deg]", "{:+2d}".format(ahrs_pitch)),
            ("Roll [deg]", "{:+2d}".format(ahrs_roll)),
        )
        starty = dashboard(draw, 250, 35, 225, True, "AHRS", lines)
    else:
        starty = 20

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
        dashboard(draw, 250, starty, 225, True, "Baro", lines)

    if error_message is not None:
        centered_text(draw, 60, error_message, verylargefont, fill="black")
    left = "Stats"
    right = "Start"
    middle = "Mode"
    draw.text((5, sizey - SMALL - 3), left, font=smallfont, fill="black")
    textlength = draw.textlength(right, smallfont)
    draw.text((sizex - textlength - 8, sizey - SMALL - 3), right, font=smallfont, fill="black", align="right")
    centered_text(draw, sizey - SMALL - 3, middle, smallfont, fill="black")


def form_line(values, key, format_str):    # generates line if key exists with form string, "---" else
    if key in values:
        return format_str.format(values[key])
    else:
        return '---'


def distance_statistics(draw, values):
    centered_text(draw, 0, "Start-/Landing Statistics", smallfont, fill="black")

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
    starty = dashboard(draw, 5, 35, 225, True, "Takeoff", lines)

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
    starty = dashboard(draw, 250, 35, 225, True, "Landing", lines)

    middle = "Back"
    centered_text(draw, sizey - SMALL - 3, middle, smallfont, fill="black")


def checklist_topic(draw, ypos, topic, highlighted=False):
    xpos = 10
    xpos_remark = 100
    xpos_sub = 50
    topic_offset = 12
    subtopic_offset = 6
    remark_offset = 4
    topic_right_offset = 6

    y = ypos
    if 'TASK' in topic:
        draw.text((xpos, ypos), topic['TASK'], font=smallfont, fill="black")    # Topic
    if 'CHECK' in topic:
        right_text(draw, ypos, topic['CHECK'], font=smallfont, fill="black", offset=topic_right_offset)     # Check
    y = y + SMALL
    if 'REMARK' in topic:   # remark
        y= y + remark_offset
        draw.text((xpos_remark, y), topic['REMARK'], font=verysmallfont, fill="black")  # remark
        y = y + VERYSMALL
    if 'TASK1' in topic:    # subtopic
        y = y + subtopic_offset
        draw.text((xpos_sub, y), topic['TASK1'], font=smallfont, fill="black")  # subtopic
        if 'CHECK1' in topic:
            right_text(draw, y, topic['CHECK1'], font=smallfont, fill="black", offset = topic_right_offset)  # subtopic check
        y = y + SMALL
    if 'TASK2' in topic:   # subtopic2
        y = y + subtopic_offset
        draw.text((xpos_sub, y), topic['TASK2'], font=smallfont, fill="black")  # subtopic
        if 'CHECK2' in topic:
            right_text(draw, y, topic['CHECK2'], font=smallfont, fill="black", offset=topic_right_offset)  # subtopic check
        y = y + SMALL
    if 'TASK3' in topic:   # subtopic3
        y = y + subtopic_offset
        draw.text((xpos_sub, y), topic['TASK3'], font=smallfont, fill="black")  # subtopic
        if 'CHECK3' in topic:
            right_text(draw, y, topic['CHECK3'], font=smallfont, fill="black", offset=topic_right_offset)  # subtopic check
        y = y + SMALL
    if highlighted:   # draw frame around whole topic
        draw.rounded_rectangle([3, ypos-4, sizex-2, y+4], width=3, radius=5, outline="black")
    return y + topic_offset


def checklist(draw, checklist_name, topi, currenti, nexti):
    centered_text(draw, 0, "Checklist: " + checklist_name, smallfont, fill="black")
    if topi:
        checklist_topic(draw, 30, topi, highlighted=False)
    if currenti:
        checklist_topic(draw, 102 , currenti, highlighted=True)
    if nexti:
        checklist_topic(draw, 172, nexti, highlighted=False)
    bottom_line(draw, "Prev", "NextList", "CheckItem")
