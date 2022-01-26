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
from PIL import Image, ImageDraw, ImageFont
import math
import time
import datetime
from pathlib import Path

# global constants
VERYLARGE = 30    # timer
MORELARGE = 28
LARGE = 24          # size of height indications of aircraft
SMALL = 20      # size of information indications on top and bottom
VERYSMALL = 18
AWESOME_FONTSIZE = 18   # bluetooth indicator
AIRCRAFT_SIZE = 4        # size of aircraft arrow
MINIMAL_CIRCLE = 10     # minimal size of mode-s circle
ARCPOSITION_EXCLUDE_FROM = 0
ARCPOSITION_EXCLUDE_TO = 0
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
draw = None
roll_posmarks = (-90, -60, -30, -20, -10, 0, 10, 20, 30, 60, 90)
pitch_posmarks = (-30, -20, -10, 10, 20, 30)
PITCH_SCALE = 4.0
msize = 15  # size of markings

# compass
compass_aircraft = None   # image of aircraft for compass-display
mask = None
cdraw = None
cmsize = 20        # length of compass marks
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
    device.async_displayPart(device.getbuffer_optimized(epaper_image))


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
    global draw
    global compass_aircraft
    global mask
    global cdraw

    device = epd1in54_V2.EPD()
    device.init(0)
    device.Clear(0xFF)   # necessary to overwrite everything
    epaper_image = Image.new('1', (device.height, device.width), 0xFF)
    draw = ImageDraw.Draw(epaper_image)
    device.init(1)
    device.Clear(0xFF)
    sizex = device.height
    sizey = device.width
    zerox = sizex / 2
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
    device.displayPart_mod(device.getbuffer_optimized(epaper_image))
    end = time.time()
    display_refresh = end-start
    # compass
    pic_path = str(Path(__file__).resolve().parent.joinpath('plane-white-96x96.bmp'))
    compass_aircraft = Image.open(pic_path)
    mask = Image.new('1', (LARGE * 2, LARGE * 2))
    cdraw = ImageDraw.Draw(mask)
    return draw, max_pixel, zerox, zeroy, display_refresh


def cleanup():
    global device

    device.init(0)
    device.Clear(0xFF)
    device.sleep_nowait()


def refresh():
    global device

    device.Clear(0xFF)  # necessary to overwrite everything
    device.init(1)


def clear(draw):
    draw.rectangle((0, 0, sizex - 1, sizey - 1), fill="white")  # clear everything in image


def centered_text(draw, y, text, font, fill):
    ts = draw.textsize(text, font)
    draw.text((zerox - ts[0] / 2, y), text, font=font, fill=fill)


def right_text(draw, y, text, font, fill):
    ts = draw.textsize(text, font)
    draw.text((sizex-5-ts[0], y), text, font=font, fill=fill)


def startup(draw, version, target_ip, seconds):
    logopath = str(Path(__file__).resolve().parent.joinpath('stratux-logo-128x128.bmp'))
    logo = Image.open(logopath)
    draw.bitmap((zerox-128/2, 0), logo, fill="black")
    versionstr = "Epaper-Radar " + version
    centered_text(draw, 160, versionstr, largefont, fill="black")
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
    tsize = draw.textsize(t, largefont)
    if tsize[0] + x + 4 * AIRCRAFT_SIZE - 2 > sizex:
        # would draw text outside, move to the left
        tposition = (x - 4 * AIRCRAFT_SIZE - tsize[0], int(y - tsize[1] / 2))
    else:
        tposition = (x + 4 * AIRCRAFT_SIZE + 1, int(y - tsize[1] / 2))
    # draw.rectangle((tposition, (tposition[0] + tsize[0], tposition[1] + LARGE)), fill="white")
    draw.text(tposition, t, font=largefont, fill="black")
    if tail is not None:
        tsize = draw.textsize(tail, verysmallfont)
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
    tsize = draw.textsize(t, largefont)
    tposition = (zerox+arctext[0]-tsize[0]/2, zeroy+arctext[1]-tsize[1]/2)
    draw.rectangle((tposition, (tposition[0]+tsize[0], tposition[1]+LARGE)), fill="white")
    draw.text(tposition, t, font=largefont, fill="black")
    if tail is not None:
        tsize = draw.textsize(tail, verysmallfont)
        draw.rectangle((tposition[0], tposition[1] + LARGE, tposition[0] + tsize[0],
                        tposition[1] + LARGE + VERYSMALL), fill="white")
        draw.text((tposition[0], tposition[1] + LARGE), tail, font=verysmallfont, fill="black")


def situation(draw, connected, gpsconnected, ownalt, course, range, altdifference, bt_devices, sound_active,
              gps_quality, gps_h_accuracy, optical_bar, basemode, extsound):
    draw.ellipse((zerox-max_pixel/2, zeroy-max_pixel/2, zerox+max_pixel/2-2, zeroy+max_pixel/2-2), outline="black")
    draw.ellipse((zerox-max_pixel/4, zeroy-max_pixel/4, zerox+max_pixel/4-1, zeroy+max_pixel/4-1), outline="black")
    draw.ellipse((zerox-2, zeroy-2, zerox+2, zeroy+2), outline="black")

    draw.text((0, 0), str(range), font=smallfont, fill="black")
    draw.text((0, SMALL), "nm", font=verysmallfont, fill="black")

    draw.text((0, sizey - SMALL), "FL" + str(round(ownalt / 100)), font=smallfont, fill="black")

    if altdifference >= 10000:
        t = str(int(altdifference / 1000)) + "k"
    else:
        t = str(altdifference)
    textsize = draw.textsize(t, smallfont)
    draw.text((sizex - textsize[0], 0), t, font=smallfont, fill="black", align="right")
    text = "ft"
    textsize = draw.textsize(text, smallfont)
    draw.text((sizex - textsize[0], SMALL), text, font=verysmallfont, fill="black", align="right")

    text = str(course) + '°'
    textsize = draw.textsize(text, smallfont)
    draw.text((sizex - textsize[0], sizey - textsize[1]), text, font=smallfont, fill="black", align="right")

    if not gpsconnected:
        centered_text(draw, 18, "No GPS", smallfont, fill="black")
    if not connected:
        centered_text(draw, 5, "No Connection!", smallfont, fill="black")

    if extsound or bt_devices > 0:
        if sound_active:
            t = ""
            if extsound:
                t += "\uf028"  # volume symbol
            if bt_devices > 0:
                t += "\uf293"  # bluetooth symbol
        else:
            t = "\uf1f6"  # bell off symbol
        textsize = draw.textsize(t, awesomefont)
        draw.text((sizex - textsize[0] - 5, sizey - SMALL), t, font=awesomefont, fill="black")

    # optical keep alive bar at right side, for the small display only 5 bars
    draw.line((sizex-6, 150+(optical_bar%5)*5, sizex-6, 150+(optical_bar%5)*5+6), fill="black", width=4)


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
    textsize = draw.textsize(right_t, smallfont)
    draw.text((sizex-textsize[0]-8, sizey-SMALL-3), right_t, font=smallfont, fill="black", align="right")
    centered_text(draw, sizey-SMALL-3, middle_text, smallfont, fill="black")


def meter(draw, current, start_value, end_value, from_degree, to_degree, size, center_x, center_y,
          marks_distance, small_marks_distance, middle_text1, middle_text2):
    big_mark_length = 15
    small_mark_length = 8
    text_distance = 4
    arrow_line_size = 8  # must be an even number
    arrow = ((arrow_line_size / 2, 0), (-arrow_line_size / 2, 0), (-arrow_line_size / 2, -size / 2 + 50),
             (0, -size / 2 + 10), (arrow_line_size / 2, -size / 2 + 50), (arrow_line_size / 2, 0))
    # points of arrow at angle 0 (pointing up) for line drawing

    deg_per_value = (to_degree - from_degree) / (end_value - start_value)

    draw.arc((center_x-size/2, center_y-size/2, center_x+size/2, center_y+size/2),
             from_degree-90, to_degree-90, width=4, fill="black")
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
        draw.line(mark, fill="black", width=3)
        # text
        marktext = str(m)
        w, h = largefont.getsize(marktext)
        t_center = translate(angle, ((0, -size/2 + big_mark_length + h/2 + text_distance), ), (center_x, center_y))
        draw.text((t_center[0][0]-w/2, t_center[0][1]-h/2), marktext, fill="black", font=largefont)
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
        ts = smallfont.getsize(middle_text1)
        draw.text((center_x-ts[0]/2, center_y-ts[1]-20), middle_text1, font=smallfont, fill="black", align="left")
    if middle_text2 is not None:
        ts = smallfont.getsize(middle_text2)
        draw.text((center_x-ts[0]/2, center_y+20), middle_text2, font=smallfont, fill="black", align="left")


def gmeter(draw, current, maxg, ming, error_message):
    gm_size = sizex
    meter(draw, current, -3, 5, 120, 420, gm_size, zerox, zeroy, 1, 0.25, "G-Force", None)

    draw.text((zerox + 13, 80), "max", font=verysmallfont, fill="black")
    right_text(draw, 80, "{:+1.2f}".format(maxg), smallfont, fill="black")
    if error_message:
        centered_text(draw, 57, error_message, largefont, fill="black")
    draw.text((zerox + 13, 102), "min", font=verysmallfont, fill="black")
    right_text(draw, 102, "{:+1.2f}".format(ming), smallfont, fill="black")

    right = "Reset"
    textsize = draw.textsize(right, verysmallfont)
    draw.text((sizex-textsize[0], sizey-SMALL), right, font=verysmallfont, fill="black", align="right")



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
    textsize = draw.textsize(text, smallfont)
    draw.text((sizex - textsize[0] - 100, sizey - textsize[1] - 5), text, font=smallfont, fill="black", align="right")
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
                w, h = draw.textsize(mark, largefont)
                cdraw.text(((LARGE * 2 - w) / 2, (LARGE * 2 - h) / 2), mark, 1, font=largefont)
            else:
                w, h = draw.textsize(mark, morelargefont)
                cdraw.text(((LARGE * 2 - w) / 2, (LARGE * 2 - h) / 2), mark, 1, font=morelargefont)
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
    ts = draw.textsize(middle_text, verysmallfont)
    draw.text((sizey/2 - ts[0]/2, sizey/2 - ts[1] - 10), middle_text, font=verysmallfont, fill="black", align="left")
    middle_text = "100 feet per min"
    ts = draw.textsize(middle_text, verysmallfont)
    draw.text((sizey/2 - ts[0] / 2, sizey/2 + 10), middle_text, font=verysmallfont, fill="black", align="left")

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
    textsize = draw.textsize(right, smallfont)
    draw.text((sizex - textsize[0] - 8, sizey - SMALL - 3), right, font=smallfont, fill="black", align="right")
    centered_text(draw, sizey - SMALL - 3, middle, smallfont, fill="black")


def shutdown(draw, countdown, shutdownmode):
    if shutdownmode == 0:   # shutdown stratux + display
        message = "Shutdown stratux & display"
    elif shutdownmode == 1:
        message = "Shutdown display"
    elif shutdownmode == 2:
        message = "Reboot"
    centered_text(draw, 10, message, largefont, fill="black")
    message = "in " + str(countdown) + " seonds!"
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
    textsize = draw.textsize(right_text, smallfont)
    draw.text((sizex - textsize[0] - 8, sizey - SMALL - 3), right_text, font=smallfont, fill="black", align="right")
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


def slip(draw, slipskid):
    slipsize = 8
    slipscale = 15
    if slipskid < -10:
        slipskid = -10
    elif slipskid > 10:
        slipskid = 10

    draw.rectangle((ah_zerox - 70, sizey - slipsize * 2, ah_zerox + 70, sizey - 1),
                   fill="black")
    draw.ellipse((ah_zerox - slipskid * slipscale - slipsize, sizey - slipsize * 2,
                  ah_zerox - slipskid * slipscale + slipsize, sizey - 1), fill="white")
    draw.line((ah_zerox, sizey - slipsize * 2, ah_zerox, sizey - 1), fill="black", width=4)
    draw.line((ah_zerox, sizey - slipsize * 2, ah_zerox, sizey - 1), fill="white", width=2)


def ahrs(draw, pitch, roll, heading, slipskid, error_message):
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
    rollmarks(draw, roll)
    # slip indicator
    slip(draw, slipskid)

    # infotext = "P:" + str(pitch) + " R:" + str(roll)
    if error_message:
        centered_text(draw, 60, error_message, smallfont, fill="black")


def text_screen(draw, headline, subline, text, left_text, middle_text, right_text):
    centered_text(draw, 0, headline, verylargefont, fill="black")
    txt_starty = VERYLARGE
    if subline is not None:
        centered_text(draw, txt_starty, subline, largefont, fill="black")
        txt_starty += LARGE
    draw.text((0, txt_starty), text, font=smallfont, fill="black")

    draw.text((0, sizey - SMALL), left_text, font=verysmallfont, fill="black")
    textsize = draw.textsize(right_text, verysmallfont)
    draw.text((sizex - textsize[0], sizey - SMALL), right_text, font=verysmallfont, fill="black", align="right")
    centered_text(draw, sizey - SMALL, middle_text, verysmallfont, fill="black")


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
    textsize = draw.textsize(right, smallfont)
    draw.text((sizex - textsize[0] - 8, sizey - SMALL - 3), right, font=smallfont, fill="black", align="right")
    centered_text(draw, sizey - SMALL - 8, middle, smallfont, fill="black")


def bar(draw, y, text, val, max_val, yellow, red, unit="", valtext=None, minval=0):
    bar_start = 100
    bar_end = 420

    draw.text((5, y), text, font=verysmallfont, fill="black", align="left")
    right_val = str(int(max_val)) + unit
    textsize = draw.textsize(right_val, verysmallfont)
    draw.text((sizex - textsize[0]-5, y), right_val, font=verysmallfont, fill="black", align="right")
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
    ts = draw.textsize(t, verysmallfont)
    draw.text(((bar_end-bar_start)/2+bar_start-ts[0]/2, y), t, font=verysmallfont, fill="black",
              stroke_width=1, stroke_fill="white")
    return y+VERYSMALL+12


def round_text(draw, x, y, text, color, yesno=True, out=None):
    ts = draw.textsize(text, verysmallfont)
    draw.rounded_rectangle([x, y-2, x+ts[0]+10, y+ts[1]+2], radius=4, fill=color, outline=out)
    draw.text((x+5, y), text, font=verysmallfont, fill="black")
    if not yesno:
        draw.line([x, y+ts[1]+2, x+ts[0]+10, y-2], fill="black", width=2)
    return x+ts[0]+20


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
        draw.text((20, starty), f[0].strftime("%d.%m.%y"), font=verysmallfont, fill="black")
        draw.text((120, starty), f[0].strftime("%H:%M"), font=verysmallfont, fill="black")
        if f[1] != 0:    # ==0 means still in the air
            delta = (f[1]-f[0]).total_seconds()
            draw.text((350, starty), f[1].strftime("%H:%M"), font=verysmallfont, fill="black")
        else:
            delta = (datetime.datetime.now(datetime.timezone.utc) - f[0]).total_seconds()
            draw.text((350, starty), "in the air", font=verysmallfont, fill="black")
        hours, remainder = divmod(delta, 3600)
        minutes, seconds = divmod(remainder, 60)
        out = '  {:02}:{:02}  '.format(int(hours), int(minutes))
        round_text(draw, 220, starty, out, "white", out="black")
        starty += VERYSMALL + 5
        maxlines -= 1
        if maxlines <= 0:
            break