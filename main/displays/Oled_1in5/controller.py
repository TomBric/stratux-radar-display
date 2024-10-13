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

import math
import time
import datetime
from pathlib import Path
from PIL import Image, ImageFont, ImageDraw
from . import radar_opts
import logging

# global constants
VERYLARGE = 24
LARGE = 18  # size of height indications of aircraft
MEDIUM = 14
SMALL = 12  # size of information indications on top and bottom
VERYSMALL = 10  # used for "nm" and "ft"
AIRCRAFT_SIZE = 3  # size of aircraft arrow
MINIMAL_CIRCLE = 10  # minimal size of mode-s circle
PITCH_SCALE = 1.5
# end definitions

rlog = None
# device properties
sizex = 0
sizey = 0
zerox = 0
zeroy = 0
verylargefont = ""
largefont = ""
mediumfont = ""
smallfont = ""
verysmallfont = ""
webfont = ""
device = None
image = None
# ahrs
ahrs_draw = None
roll_posmarks = (-90, -60, -30, -20, -10, 0, 10, 20, 30, 60, 90)
pitch_posmarks = (-30, -20, -10, 10, 20, 30)
# compass
compass_aircraft = None   # image of aircraft for compass-display
mask = None
cdraw = None
draw = None
cmsize = 10        # length of compass marks
# gmeter
m_marks = ((120, ""), (157.5, "-2"), (195, "-1"), (232.5, "0"), (270, "+1"), (307.5, "+2"), (345, "+3"),
           (382.5, "+4"), (420, ""))
# co warner
space = 3  # space between scale figures and zero line
# end device globals


def posn(angle, arm_length):
    dx = round(math.cos(math.radians(angle)) * arm_length)
    dy = round(math.sin(math.radians(angle)) * arm_length)
    return dx, dy


def make_font(name, size):
    font_path = str(Path(__file__).resolve().parent.joinpath('fonts', name))
    return ImageFont.truetype(font_path, size)


def init(fullcircle=False):
    global sizex
    global sizey
    global zerox
    global zeroy
    global verylargefont
    global largefont
    global mediumfont
    global smallfont
    global verysmallfont
    global webfont
    global device
    global image
    global compass_aircraft
    global mask
    global cdraw
    global draw

    rlog = logging.getLogger('stratux-radar-log')
    config_path = str(Path(__file__).resolve().parent.joinpath('ssd1351.conf'))
    device = radar_opts.get_device(['-f', config_path])
    image = Image.new(device.mode, device.size)
    draw = ImageDraw.Draw(image)
    sizex = device.width
    sizey = device.height
    zerox = sizex / 2
    zeroy = sizey / 2
    rlog.debug(f'Oled_1in5 selected: sizex={sizex} sizey={sizey} zero=({zerox}, {zeroy})')
    device.contrast(255)  # set full contrast
    verylargefont = make_font("Font.ttc", VERYLARGE)
    largefont = make_font("Font.ttc", LARGE)  # font for height indications
    mediumfont = make_font("Font.ttc", MEDIUM)
    smallfont = make_font("Font.ttc", SMALL)  # font for information indications
    verysmallfont = make_font("Font.ttc", VERYSMALL)  # font for information indications
    webfont = make_font("fontawesome-webfont.ttf", SMALL)  # font for Bluetooth indications
    start = time.time()
    # do sync version of display to measure time
    device.display(image)
    end = time.time()
    display_refresh = end - start
    # compass
    pic_path = str(Path(__file__).resolve().parent.joinpath('plane-white-64x64.bmp'))
    compass_aircraft = Image.open(pic_path).convert("RGBA")
    mask = Image.new('1', (LARGE * 2, LARGE * 2))
    cdraw = ImageDraw.Draw(mask)
    return sizex, zerox, zeroy, display_refresh


def cleanup():
    device.cleanup()


def centered_text(y, text, font, fill):
    tl = draw.textlength(text, font)
    draw.text((zerox - tl / 2, y), text, font=font, fill=fill)


def bottom_line(left, middle, right, offset=0):  # offset to be able to print letters like p and q
    draw.text((0, sizey - SMALL - offset), left, font=smallfont, fill="green")
    textlength = draw.textlength(right, smallfont)
    draw.text((sizex - textlength, sizey - SMALL - offset), right, font=smallfont, fill="green", align="right")
    centered_text(sizey - SMALL - offset, middle, smallfont, fill="green")


def right_text(y, text, font, fill, offset=0):
    tl = draw.textlength(text, font)
    draw.text((sizex - tl - offset, y), text, font=font, fill=fill)


def display():
    device.display(image)


def is_busy():
    # oled is never busy, no refresh
    return False


def next_arcposition(old_arcposition):
    # defines next position of height indicator on circle. Can be used to exclude several ranges or
    # be used to define the next angle on the circle
    return (old_arcposition + 210) % 360


def clear():
    draw.rectangle((0, 0, sizex - 1, sizey - 1), fill="black")


def refresh():
    pass  # nothing to do for Oled, does not need a refresh function


def startup(version, target_ip, seconds):
    logopath = str(Path(__file__).resolve().parent.joinpath('stratux-logo-64x64.bmp'))
    logo = Image.open(logopath)
    draw.rectangle(((0, 0), (sizex, 64)), fill="blue")
    draw.bitmap((zerox - 32, 0), logo, fill="white")
    centered_text(64, "Radar "+version, largefont, fill="white")
    centered_text(sizey - 3 * SMALL, "Connecting to", smallfont, fill="white")
    centered_text(sizey - 2*SMALL, target_ip, smallfont, fill="white")
    display()
    time.sleep(seconds)


def aircraft(x, y, direction, height, vspeed, nspeed_length, tail):
    p1 = posn(270 + direction, 2 * AIRCRAFT_SIZE)
    p2 = posn(270 + direction + 150, 4 * AIRCRAFT_SIZE)
    p3 = posn(270 + direction + 180, 2 * AIRCRAFT_SIZE)
    p4 = posn(270 + direction + 210, 4 * AIRCRAFT_SIZE)
    p5 = posn(270 + direction, nspeed_length)  # line for speed

    draw.polygon(((x + p1[0], y + p1[1]), (x + p2[0], y + p2[1]), (x + p3[0], y + p3[1]), (x + p4[0], y + p4[1])),
                 fill="red", outline="white")
    draw.line((x + p1[0], y + p1[1], x + p5[0], y + p5[1]), fill="white", width=1)
    if height >= 0:
        t = "+" + str(abs(height))
    else:
        t = "-" + str(abs(height))
    if vspeed > 0:
        t = t + '\u2191'
    if vspeed < 0:
        t = t + '\u2193'
    tl = draw.textlength(t, largefont)
    if tl + x + 4 * AIRCRAFT_SIZE - 2 > sizex:
        # would draw text outside, move to the left
        tposition = (x - 4 * AIRCRAFT_SIZE - tl, int(y - LARGE / 2))
    else:
        tposition = (x + 4 * AIRCRAFT_SIZE + 1, int(y - LARGE / 2))
    draw.rectangle((tposition, (tposition[0] + tl, tposition[1] + LARGE)), fill="black")
    draw.text(tposition, t, font=largefont, fill="white")


def modesaircraft(radius, height, arcposition, vspeed, tail):
    if radius < MINIMAL_CIRCLE:
        radius = MINIMAL_CIRCLE
    draw.ellipse((64 - radius, 64 - radius, 64 + radius, 64 + radius), width=3, outline="white")
    arctext = posn(arcposition, radius)
    if height > 0:
        signchar = "+"
    else:
        signchar = "-"
    t = signchar + str(abs(height))
    if vspeed > 0:
        t = t + '\u2191'
    if vspeed < 0:
        t = t + '\u2193'
    tl = draw.textlength(t, largefont)
    tposition = (64 + arctext[0] - tl / 2, 64 + arctext[1] - LARGE / 2)
    draw.rectangle((tposition, (tposition[0] + tl, tposition[1] + LARGE)), fill="black")
    draw.text(tposition, t, font=largefont, fill="white")


def situation(connected, gpsconnected, ownalt, course, range, altdifference, bt_devices, sound_active,
              gps_quality, gps_h_accuracy, optical_alive, basemode, extsound, co_alarmlevel, co_alarmstring):
    draw.ellipse((0, 0, sizex - 1, sizey - 1), outline="floralwhite")
    draw.ellipse((sizex / 4, sizey / 4, zerox + sizex / 4, zeroy + sizey / 4), outline="floralwhite")
    draw.ellipse((zerox - 2, zeroy - 2, zerox + 2, zeroy + 2), outline="floralwhite")
    draw.text((0, sizey - SMALL), "FL" + str(round(ownalt / 100)), font=smallfont, fill="floralwhite")

    draw.text((0, 0), str(range), font=smallfont, fill="floralwhite")
    draw.text((0, SMALL), "nm", font=verysmallfont, fill="floralwhite")

    if altdifference >= 10000:
        t = str(int(altdifference / 1000)) + "k"
    else:
        t = str(altdifference)
    tl = draw.textlength(t, smallfont)
    draw.text((sizex - tl, 0), t, font=smallfont, fill="floralwhite", align="right")

    text = "ft"
    tl = draw.textlength(text, smallfont)
    draw.text((sizex - tl, SMALL), text, font=verysmallfont, fill="floralwhite", align="right")

    text = str(course) + '°'
    tl = draw.textlength(text, smallfont)
    draw.text((sizex - tl, sizey - SMALL), text, font=smallfont, fill="floralwhite", align="right")

    if extsound or bt_devices > 0:   # extsound means and sound devices has been found
        if sound_active:   # means user left sound switched on
            if extsound:
                btcolor = "orange"
                text = "\uf028"  # volume symbol
                if bt_devices > 0:
                    btcolor = "blue"
            else:   # bt_devices is > 0 anyhow
                btcolor = "blue"
                text = '\uf293'  # bluetooth symbol
        else:
            btcolor = "red"
            text = '\uf1f6'  # bell off symbol
        tl = draw.textlength(text, webfont)
        draw.text((sizex - tl, sizey - 2 * SMALL), text, font=webfont, fill=btcolor, align="right")

    if not gpsconnected:
        centered_text(0, "No GPS", smallfont, fill="red")
    if not connected:
        centered_text(zeroy, "No Connection!", smallfont, fill="red")
    if co_alarmlevel > 0:
        centered_text(sizey-3*SMALL, "CO Alarm!", smallfont, fill="red")
        centered_text(sizey-2*SMALL, co_alarmstring, smallfont, fill="red")
    if basemode:
        text = "Ground mode"
        tl = draw.textlength(text, smallfont)
        centered_text(sizey - SMALL, text, smallfont, fill="red")


def timer(utctime, stoptime, laptime, laptime_head, left_text, middle_text, right_text, timer_runs):
    draw.text((0, 0), "UTC", font=smallfont, fill="cyan")
    centered_text(SMALL, utctime, verylargefont, fill="yellow")
    draw.text((0, SMALL + VERYLARGE), "Timer", font=smallfont, fill="cyan")
    if timer_runs:
        color = "lavender"
    else:
        color = "orangered"
    centered_text(2 * SMALL + VERYLARGE, stoptime, verylargefont, fill=color)
    draw.text((0, 2 * SMALL + 2 * VERYLARGE), laptime_head, font=smallfont, fill="cyan")
    if laptime_head == "Laptimer":
        centered_text(3 * SMALL + 2 * VERYLARGE, laptime, verylargefont, fill="powderblue")
    else:
        centered_text(3 * SMALL + 2 * VERYLARGE, laptime, verylargefont, fill="magenta")

    bottom_line(left_text, middle_text, right_text, offset=3)


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


def meter(current, start_value, end_value, from_degree, to_degree, size, center_x, center_y,
          marks_distance, small_marks_distance, middle_text1, middle_text2):
    big_mark_length = 7
    small_mark_length = 4
    text_distance = 3
    arrow_line_size = 6  # must be an even number
    arrow_head_size = 15
    arrow_distance = 5
    arrow = ((arrow_line_size / 2, 0), (-arrow_line_size / 2, 0), (-arrow_line_size / 2, -size / 2 + arrow_head_size),
             (0, -size / 2 + arrow_distance), (arrow_line_size / 2, -size / 2 + arrow_head_size),
             (arrow_line_size / 2, 0))
    # points of arrow at angle 0 (pointing up) for line drawing

    deg_per_value = (to_degree - from_degree) / (end_value - start_value)

    draw.arc((center_x-size/2, center_y-size/2, center_x+size/2, center_y+size/2),
             from_degree-90, to_degree-90, width=2, fill="white")
    # small marks first
    line = ((0, -size/2), (0, -size/2+small_mark_length))
    m = start_value
    while m <= end_value:
        angle = deg_per_value * (m-start_value) + from_degree
        mark = translate(angle, line, (center_x, center_y))
        draw.line(mark, fill="white", width=1)
        m += small_marks_distance
    # large marks
    line = ((0, -size/2), (0, -size/2+big_mark_length))
    m = start_value
    while m <= end_value:
        angle = deg_per_value*(m-start_value) + from_degree
        mark = translate(angle, line, (center_x, center_y))
        draw.line(mark, fill="white", width=2)
        # text
        marktext = str(m)
        tl = draw.textlength(marktext, largefont)
        t_center = translate(angle, ((0, -size/2 + big_mark_length + LARGE/2 + text_distance), ), (center_x, center_y))
        draw.text((t_center[0][0]-tl/2, t_center[0][1]-LARGE/2), marktext, fill="white", font=largefont)
        m += marks_distance
    # arrow
    if current > end_value:   # normalize values in allowed ranges
        current = end_value
    elif current < start_value:
        current = start_value
    angle = deg_per_value * (current - start_value) + from_degree
    ar = translate(angle, arrow, (center_x, center_y))
    draw.line(ar, fill="white", width=1)
    # centerpoint
    draw.ellipse((center_x - 5, center_y - 5, center_x + 5, center_y + 5), fill="white")

    if middle_text1 is not None:
        tl = draw.textlength(middle_text1, smallfont)
        draw.text((center_x-tl/2, center_y-SMALL-15), middle_text1, font=smallfont, fill="yellow", align="left")
    if middle_text2 is not None:
        tl = draw.textlength(smiddle_text2, smallfont)
        draw.text((center_x-tl/2, center_y+15), middle_text2, font=smallfont, fill="yellow", align="left")


def gmeter(current, maxg, ming, error_message):
    meter(current, -3, 5, 120, 420, sizex-2, sizex/2, sizex/2, 1, 0.25, "G-Meter", None)
    draw.text((zerox+8, 52), "max", font=smallfont, fill="cyan")
    right_text(52, "{:+1.2f}".format(maxg), smallfont, fill="magenta")
    if error_message:
        centered_text(57, error_message, largefont, fill="red")
    draw.text((zerox+8, 65), "min", font=smallfont, fill="cyan")
    right_text(65, "{:+1.2f}".format(ming), smallfont, fill="magenta")

    bottom_line("", "", "Reset")


def compass(heading, error_message):
    csize = sizex/2   # radius of compass rose

    draw.ellipse((0, 0, sizex-1, sizey-1), outline="white", fill="black", width=2)
    image.paste(compass_aircraft, (round(zerox) - 30, 30))
    draw.line((zerox, 10, zerox, 30), fill="white", width=1)
    text = str(heading) + '°'
    tl = draw.textlength(text, smallfont)
    draw.text((sizex - tl, sizey - SMALL), text, font=smallfont, fill="floralwhite", align="right")
    for m in range(0, 360, 10):
        s = math.sin(math.radians(m - heading + 90))
        c = math.cos(math.radians(m - heading + 90))
        if m % 30 != 0:
            draw.line((zerox-(csize-1)*c, zeroy-(csize-1)*s, zerox-(csize-cmsize)*c, zeroy-(csize-cmsize)*s),
                      fill="white", width=1)
        else:
            draw.line((zerox - (csize - 1) * c, zeroy - (csize - 1) * s, zerox - (csize - cmsize) * c,
                       zeroy - (csize - cmsize) * s), fill="white", width=3)
            color = "yellow"
            if m == 0:
                mark = "N"
            elif m == 90:
                mark = "E"
            elif m == 180:
                mark = "S"
            elif m == 270:
                mark = "W"
            else:
                mark = str(int(m/10))
                color = "white"
            cdraw.rectangle((0, 0, LARGE*2, LARGE*2), fill="black")
            tl = draw.textlength(mark, largefont)
            cdraw.text(((LARGE*2-tl)/2, LARGE/2), mark, 1, font=largefont)
            rotmask = mask.rotate(-m+heading, expand=False)
            center = (zerox - (csize - cmsize - LARGE / 2) * c, zeroy - (csize - cmsize - LARGE / 2) * s)
            image.paste(color, (round(center[0]-LARGE), round(center[1]-LARGE)), rotmask)
    if error_message is not None:
        centered_text(57, error_message, largefont, fill="red")


def vsi(vertical_speed, flight_level, gps_speed, gps_course, gps_altitude, vertical_max, vertical_min,
        error_message):
    csize = sizex / 2  # radius of vsi
    vmsize_n = 8
    vmsize_l = 14

    draw.arc((zerox - csize, 0, zerox + csize - 1, sizey - 1), 10, 350, fill="white", width=2)
    draw.text((12, zeroy - VERYSMALL - 12), "up", font=verysmallfont, fill="white", align="left")
    draw.text((12, zeroy + 12), "dn", font=verysmallfont, fill="white", align="left")
    middle_text = "Vert Spd"
    tl = draw.textlength(middle_text, verysmallfont)
    draw.text((zerox - tl / 2, zeroy - VERYSMALL - 10), middle_text, font=verysmallfont, fill="white", align="left")
    middle_text = "100 ft/min"
    tl = draw.textlength(middle_text, verysmallfont)
    draw.text((zerox - tl / 2, zeroy + 10), middle_text, font=verysmallfont, fill="white", align="left")

    scale = 170.0 / 2000.0
    for m in range(-2000, 2100, 100):
        s = math.sin(math.radians(m * scale))
        c = math.cos(math.radians(m * scale))
        if m % 500 != 0:
            draw.line((zerox - (csize - 1) * c, zeroy - (csize - 1) * s, zerox - (csize - vmsize_n) * c,
                       zeroy - (csize - vmsize_n) * s), fill="white", width=1)
        else:
            draw.line((zerox - (csize - 1) * c, zeroy - (csize - 1) * s, zerox - (csize - vmsize_l) * c,
                       zeroy - (csize - vmsize_l) * s), fill="white", width=3)
            mark = str(round(abs(m / 100)))
            tl = draw.textlength(mark, largefont)
            if m != 2000 and m != -2000:
                center = (zerox-(csize-1-vmsize_l-LARGE/2) * c, zeroy-(csize-5-vmsize_l-LARGE/2) * s)
                draw.text((center[0] - tl / 2, center[1] - LARGE / 2), mark, fill="white", font=largefont)
            if m == 2000:  # put 2 in the middle at 180 degrees
                draw.text((zerox + (csize - 1 - vmsize_l - LARGE / 2) - tl / 2, zeroy - 1 - LARGE / 2), mark,
                          fill="white", font=largefont)

    if error_message is not None:
        centered_text(30, error_message, largefont, fill="red")

    vert_val = vertical_speed * scale  # normalize from -170 to 170 degrees
    if vert_val > 170.0:  # set max / min values
        vert_val = 170.0
    elif vert_val < -170.0:
        vert_val = -170.0
    s = math.sin(math.radians(vert_val))
    c = math.cos(math.radians(vert_val))
    draw.line((zerox - (csize - vmsize_n - 3) * c, zeroy - (csize - vmsize_n - 3) * s, zerox, zeroy), fill="white",
              width=1)
    draw.line((zerox - (csize - vmsize_l - 3) * c, zeroy - (csize - vmsize_l - 3) * s,
               zerox + 16 * c, zeroy + 16 * s), fill="white", width=5)
    draw.ellipse((zerox - 4, zeroy - 4, zerox + 4, zeroy + 4), outline="white", fill="black", width=2)


def shutdown(countdown, shutdownmode):
    message = ""
    if shutdownmode == 0:   # shutdown stratux + display
        message = "Shutdown all"
    elif shutdownmode == 1:
        message = "Shtdwn displ"
    elif shutdownmode == 2:
        message = "Reboot"
    centered_text(10, message, largefont, fill="white")
    message = "in " + str(countdown) + " seconds!"
    centered_text(30, message, largefont, fill="white")
    message = "Left to cancel ..."
    centered_text(60, message, smallfont, fill="white")
    message = "Middle display only ..."
    centered_text(75, message, smallfont, fill="white")
    message = "Right for reboot all ..."
    centered_text(90, message, smallfont, fill="white")

    bottom_line("Canc", "Displ", "Rebo", offset=3)


def rollmarks(roll):
    for rm in roll_posmarks:
        s = math.sin(math.radians(rm - roll + 90))
        c = math.cos(math.radians(rm - roll + 90))
        if rm % 30 == 0:
            draw.line((zerox - zerox * c, zeroy - zerox * s, zerox - (zerox - 8) * c, zeroy - (zerox - 8) * s),
                      fill="white", width=2)
        else:
            draw.line((zerox - zerox * c, zeroy - zerox * s, zerox - (zerox - 5) * c, zeroy - (zerox - 5) * s),
                      fill="white", width=1)
    draw.polygon((zerox, 10, zerox - 5, 10 + 5, zerox + 5, 10 + 5), fill="white")


def linepoints(pitch, roll, pitch_distance, length):
    s = math.sin(math.radians(180 + roll))
    c = math.cos(math.radians(180 + roll))
    dist = (-pitch + pitch_distance) * PITCH_SCALE
    move = (dist * s, dist * c)
    s1 = math.sin(math.radians(-90 - roll))
    c1 = math.cos(math.radians(-90 - roll))
    p1 = (zerox - length * s1, zeroy + length * c1)
    p2 = (zerox + length * s1, zeroy - length * c1)
    ps = (p1[0] + move[0], p1[1] + move[1])
    pe = (p2[0] + move[0], p2[1] + move[1])
    return ps, pe


def slip(slipskid):
    slipsize = 5
    slipscale = 3
    if slipskid < -10:
        slipskid = -10
    elif slipskid > 10:
        slipskid = 10

    draw.rectangle((zerox - 40, device.height - slipsize * 2, zerox + 40, device.height - 1), fill="black")
    draw.ellipse((zerox - slipskid * slipscale - slipsize, device.height - slipsize * 2,
                  zerox - slipskid * slipscale + slipsize, device.height - 1), fill="white")


def ahrs(pitch, roll, heading, slipskid, error_message):
    # print("AHRS: pitch ", pitch, " roll ", roll, " heading ", heading, " slipskid ", slipskid)
    h1, h2 = linepoints(pitch, roll, 0, 200)  # horizon points
    h3, h4 = linepoints(pitch, roll, -180, 200)
    draw.polygon((h1, h2, h4, h3), fill="brown")  # earth
    h3, h4 = linepoints(pitch, roll, 180, 200)
    draw.polygon((h1, h2, h4, h3), fill="blue")  # sky
    draw.line((h1, h2), fill="white", width=2)  # horizon line
    for pm in pitch_posmarks:  # pitchmarks
        draw.line((linepoints(pitch, roll, pm, 10)), fill="white", width=1)

    # pointer in the middle
    draw.line((zerox - 30, zeroy, zerox - 15, zeroy), width=4, fill="white")
    draw.line((zerox + 30, zeroy, zerox + 15, zeroy), width=4, fill="white")
    draw.polygon((zerox, zeroy + 2, zerox - 10, zeroy + 8, zerox + 10, zeroy + 8), fill="white")

    # roll indicator
    rollmarks(roll)
    # slip indicator
    slip(slipskid)

    # infotext = "P:" + str(pitch) + " R:" + str(roll)
    if error_message:
        centered_text(30, error_message, smallfont, fill="red")
    left_text = "Levl"
    right_text = "Zero"
    draw.text((0, sizey - SMALL), left_text, font=smallfont, fill="white")
    tl = draw.textlength(right_text, smallfont)
    draw.text((sizex - tl, sizey - SMALL), right_text, font=smallfont, fill="white", align="right")


def text_screen(headline, subline, text, left, middle, right):
    centered_text(0, headline, mediumfont, fill="yellow")
    txt_starty = LARGE
    if subline is not None:
        centered_text(LARGE, subline, smallfont, fill="yellow")
        txt_starty += LARGE
    draw.text((0, txt_starty), text, font=smallfont, fill="white")
    draw.text((0, sizey - SMALL - 3), left, font=smallfont, fill="green")
    tl = draw.textlength(right, smallfont)
    draw.text((sizex - tl, sizey - SMALL - 3), right, font=smallfont, fill="green", align="right")
    centered_text(sizey - SMALL - 3, middle, smallfont, fill="green")


def screen_input(headline, subline, text, left, middle, right, prefix, inp, suffix):
    centered_text(0, headline, mediumfont, fill="yellow")
    txt_starty = LARGE
    if subline is not None:
        centered_text(LARGE, subline, smallfont, fill="yellow")
        txt_starty += LARGE
    bbox = draw.textbbox((0, txt_starty), text, font=smallfont)
    draw.text((0, txt_starty), text, font=smallfont, fill="white")
    bbox_p = draw.textbbox((bbox[0], bbox[3]), prefix, font=mediumfont)
    draw.text((bbox[0], bbox[3]), prefix, fill="white", font=mediumfont)
    bbox_rect = draw.textbbox((bbox_p[2], bbox[3]), inp, font=mediumfont)
    draw.rectangle(bbox_rect, fill="red")
    draw.text((bbox_rect[0], bbox[3]), inp, font=mediumfont, fill="black")
    draw.text((bbox_rect[2], bbox[3]), suffix, font=mediumfont, fill="white")

    draw.text((0, sizey - SMALL - 3), left, font=smallfont, fill="green")
    tl = draw.textlength(right, smallfont)
    draw.text((sizex - tl, sizey - SMALL - 3), right, font=smallfont, fill="green", align="right")
    centered_text(sizey - SMALL - 3, middle, smallfont, fill="green")


def bar(y, text, val, max_val, yellow, red, unit="", valtext=None, minval=0):
    bar_start = 30
    bar_end = 100

    draw.text((0, y), text, font=verysmallfont, fill="white", align="left")
    right_val = str(int(max_val)) + unit
    tl = draw.textlength(right_val, verysmallfont)
    draw.text((sizex - tl, y), right_val, font=verysmallfont, fill="white", align="right")
    draw.rounded_rectangle([bar_start-2, y-2, bar_end+2, y+VERYSMALL+2], radius=3, fill=None, outline="white", width=1)
    if red == 0:
        color = "DimGray"
    elif val >= red:
        color = "red"
    elif val >= yellow:
        color = "DarkOrange"
    else:
        color = "green"
    if val < minval:
        val = minval   # to display a minimum bar, valtext should be provided in this case
    if max_val != 0:
        xval = bar_start + (bar_end - bar_start) * val / max_val
    else:
        xval = bar_start
    draw.rectangle([bar_start, y, xval, y+VERYSMALL], fill=color, outline=None)
    if valtext is not None:
        t = valtext
    else:
        t = str(val)
    tl = draw.textlength(t, verysmallfont)
    draw.text(((bar_end-bar_start)/2+bar_start-tl/2, y), t, font=verysmallfont, fill="white")
    return y+VERYSMALL+5


def round_text(x, y, text, color):
    tl = draw.textlength(text, verysmallfont)
    draw.rounded_rectangle([x-2, y-1, x+tl+2, y+VERYSMALL+2], radius=4, fill=color)
    draw.text((x, y), text, font=verysmallfont, fill="white")
    return x+tl+5


def centered_round_text(y, text, color):
    tl = draw.textlength(text, verysmallfont)
    x = sizex/2 - tl/2  # center box
    draw.rounded_rectangle([x-2, y-1, x+tl+2, y+VERYSMALL+2], radius=4, fill=color)
    draw.text((x, y), text, font=verysmallfont, fill="white")
    return x+tl+5


def stratux(stat, altitude, gps_alt, gps_quality):
    starty = 0
    centered_text(0, "Stratux " + stat['version'], smallfont, fill="yellow")
    starty += SMALL+3
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
    if gps_quality == 1:
        t = "3D GPS"
    elif gps_quality == 2:
        t = "DGNSS"
    else:
        t = "GPS"
    draw.text((0, starty), t, font=verysmallfont, fill="white")
    draw.rounded_rectangle([35, starty, 55, starty + VERYSMALL + 1], radius=4, fill="green", outline=None)
    draw.rounded_rectangle([55, starty, 75, starty + VERYSMALL + 1], radius=4, fill="DarkOrange", outline=None)
    draw.rounded_rectangle([75, starty, 95, starty + VERYSMALL + 1], radius=4, fill="red", outline=None)
    t = str(stat['GPS_satellites_locked'])
    tl = draw.textlength(t, verysmallfont)
    draw.text((48-tl/2, starty), t, font=verysmallfont, fill="white", align="middle")
    t = str(stat['GPS_satellites_seen'])
    tl = draw.textlength(t, verysmallfont)
    draw.text((67-tl/2, starty), t, font=verysmallfont, fill="white", align="middle")
    t = str(stat['GPS_satellites_tracked'])
    tl = draw.textlength(t, verysmallfont)
    draw.text((87-tl/2, starty), t, font=verysmallfont, fill="white", align="middle")
    if stat['GPS_position_accuracy'] < 19999:
        gps = str(round(stat['GPS_position_accuracy'], 1)) + "m"
    else:
        gps = "NoFix"
    tl = draw.textlength(gps, verysmallfont)
    draw.text((sizex - tl, starty), gps, font=verysmallfont, fill="white")
    starty += VERYSMALL+4

    x = round_text(3, starty, "P-Alt {0:.0f}ft".format(altitude), "DarkBlue")
    round_text(x, starty, "Corr {0:+}ft".format(stat['AltitudeOffset']), "DimGray")
    starty += VERYSMALL + 4

    if stat['IMUConnected']:
        col = "green"
    else:
        col = "red"
    x = round_text(3, starty, "IMU", col)
    if stat['BMPConnected']:
        col = "green"
    else:
        col = "red"
    x = round_text(x, starty, "BMP", col)
    if stat['GPS_position_accuracy'] < 19999:
        alt = '{:5.0f}'.format(gps_alt)
    else:
        alt = " --- "
    round_text(x, starty, "GPS"+alt+"ft", "DarkBlue")

    bottom_line("+10ft", "Mode", "-10ft")


def flighttime(last_flights):
    starty = 0
    centered_text(0, "Flight Logs", smallfont, fill="yellow")
    starty += SMALL + 5

    draw.text((0, starty), "Date", font=verysmallfont, fill="white")
    draw.text((35, starty), "Start", font=verysmallfont, fill="white")
    draw.text((70, starty), "Dur", font=verysmallfont, fill="white")
    draw.text((105, starty), "Ldg", font=verysmallfont, fill="white")
    starty += VERYSMALL + 3

    maxlines = 7
    for f in last_flights:
        draw.text((0, starty), f[0].strftime("%d.%m."), font=verysmallfont, fill="green")
        draw.text((30, starty), f[0].strftime("%H:%M"), font=verysmallfont, fill="white")
        if f[1] != 0:  # ==0 means still in the air
            delta = (f[1] - f[0]).total_seconds()
            draw.text((100, starty), f[1].strftime("%H:%M"), font=verysmallfont, fill="white")
        else:
            delta = (datetime.datetime.now(datetime.timezone.utc) - f[0]).total_seconds()
            draw.text((100, starty), "in air", font=verysmallfont, fill="red")
        hours, remainder = divmod(delta, 3600)
        minutes, seconds = divmod(remainder, 60)
        out = '{:02}:{:02}'.format(int(hours), int(minutes))
        round_text(65, starty, out, "DarkBlue")
        starty += VERYSMALL + 1
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
    draw.text((xpos - tl - space, vlmin_y - VERYSMALL), str(minvalue), font=verysmallfont, fill="white")

    vl1_y = ypos + ysize - ysize * (value_line1 - minvalue) / (maxvalue - minvalue)
    tl = draw.textlength(str(value_line1), verysmallfont)
    draw.text((xpos - tl - space, vl1_y - VERYSMALL/2), str(value_line1), font=verysmallfont, fill="white")

    vl2_y = ypos + ysize - ysize * (value_line2 - minvalue) / (maxvalue - minvalue)
    tl = draw.textlength(str(value_line2), verysmallfont)
    draw.text((xpos - tl - space, vl2_y - VERYSMALL/2), str(value_line2), font=verysmallfont, fill="white")

    vlmax_y = ypos
    tl = draw.textlength(str(maxvalue), verysmallfont)
    draw.text((xpos - tl - space, vlmax_y - VERYSMALL/2), str(maxvalue), font=verysmallfont, fill="white")

    draw.rectangle((xpos, ypos, xpos+xsize-1, ypos+ysize-1), outline="white", width=1, fill="black")

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
        draw.line((x, ypos+ysize-1-5, x, ypos+ysize-1+3), width=1, fill="white")
        timestr = time.strftime("%H:%M", time.gmtime(math.floor(acttime - (no_of_time-i) * time_offset)))
        draw.text((x - tl/2, ypos+ysize-1 + 1), timestr, font=verysmallfont, fill="white")
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
            draw.line([lastpoint, (x, y)], fill="cyan", width=2)
        else:
            x = xpos
        lastpoint = (x, y)
    # value_line 1
    y = math.floor(ypos + ysize - ysize * (value_line1 - minvalue) / (maxvalue - minvalue))
    for x in range(int(xpos), int(xpos+xsize), 6):
        draw.line([(x, y), (x + 3, y)], fill="white", width=1)
    # value_line 2
    y = math.floor(ypos + ysize - ysize * (value_line2 - minvalue) / (maxvalue - minvalue))
    for x in range(int(xpos), int(xpos+xsize), 6):
        draw.line([(x, y), (x + 3, y)], fill="white", width=1)


def cowarner(co_values, co_max, r0, timeout, alarmlevel, alarmppm, alarmperiod):   # draw graph and co values
    if alarmlevel == 0:
        centered_text(0, "CO: No CO alarm", smallfont, fill="yellow")
    else:
        if alarmperiod > 60:
            alarmstr = "CO: {:d}ppm>{:d}min".format(alarmppm, math.floor(alarmperiod/60))
        else:
            alarmstr = "CO: {:d}ppm>{:d} sec".format(alarmppm, math.floor(alarmperiod))
        centered_text(0, alarmstr, smallfont, fill="red")
    graph(0, SMALL+5, sizex-12, sizey-55, co_values, 0, 120, 50, 100, timeout)
    # draw.text((320, 50 + SMALL - VERYSMALL), "Warnlevel:", font=verysmallfont, fill="black")
    # right_text(50, "{:3d}".format(alarmlevel), smallfont, fill="black")

    if len(co_values) > 0:
        act = co_values[len(co_values) - 1]
        if act < 50:
            color = "green"
        else:
            color = "red"
        round_text(5, sizey-2*SMALL-5, "CO act: {:3d}".format(act), color)
    if co_max < 50:
        color = "green"
    else:
        color = "red"
    round_text(sizex/2+5, sizey - 2 * SMALL - 5, "CO max: {:3d}".format(co_max), color)

    bottom_line("Cal", "Mode", "Reset")


def dashboard(x, y, sizex, lines):
    # dashboard, arguments are lines = ("text", "value"), ....
    starty = y
    for line in lines:
        draw.text((x, starty), line[0], font=smallfont, fill="white", align="left")
        tl = draw.textlength(line[1], smallfont)
        draw.text((x+sizex-tl, starty), line[1], font=smallfont, fill="white")
        starty += SMALL+2
    return starty


def distance(now, gps_valid, gps_quality, gps_h_accuracy, distance_valid, gps_distance, gps_speed, baro_valid,
             own_altitude, alt_diff, alt_diff_takeoff, vert_speed, ahrs_valid, ahrs_pitch, ahrs_roll,
             ground_distance_valid, grounddistance, error_message):
    centered_text(0, "GPS-Distance", smallfont, fill="yellow")
    gps_dist_str = "---"
    gps_speed_str = "---"
    if distance_valid:
        gps_dist_str = "{:4.0f}".format(gps_distance)
    if gps_valid:
        gps_speed_str = "{:3.1f}".format(gps_speed)
    lines = (
        ("UTC", "{:0>2d}:{:0>2d}:{:0>2d},{:1d}".format(now.hour, now.minute, now.second,
                                                       math.floor(now.microsecond / 100000))),
        ("GPS-Dist[m]", gps_dist_str),
        ("GPS-Spd[kts]", gps_speed_str),
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
        centered_text(80, error_message, verylargefont, fill="red")
    bottom_line("Stats/Set", "  Mode", "Start")


def form_line(values, key, format_str):    # generates line if key exists with form string, "---" else
    if key in values:
        return format_str.format(values[key])
    else:
        return '---'


def distance_statistics(values, gps_valid, gps_altitude, dest_altitude, dest_alt_valid, ground_warnings):
    centered_text(0, "Start-/Landing", smallfont, fill="yellow")

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
            draw.text((xpos, ypos), topic['TASK'], font=verysmallfont, fill="white")  # Topic
    if 'CHECK' in topic and topic['CHECK'] is not None:
        if toprint:
            right_text(ypos, topic['CHECK'], font=verysmallfont, fill="yellow", offset=topic_right_offset)
    y += SMALL
    if 'REMARK' in topic and topic['REMARK'] is not None:  # remark
        y += remark_offset
        if toprint:
            draw.text((xpos_remark, y), topic['REMARK'], font=verysmallfont, fill="white")  # remark
        y += VERYSMALL
    if 'TASK1' in topic and topic['TASK1'] is not None:  # subtopic
        y += subtopic_offset
        if toprint:
            draw.text((xpos_sub, y), topic['TASK1'], font=verysmallfont, fill="white")  # subtopic
        if 'CHECK1' in topic and topic['CHECK1'] is not None:
            if toprint:
                right_text(y, topic['CHECK1'], font=smallfont, fill="yellow", offset=topic_right_offset)
        y += VERYSMALL
    if 'TASK2' in topic and topic['TASK2'] is not None:  # subtopic2
        y += subtopic_offset
        if toprint:
            draw.text((xpos_sub, y), topic['TASK2'], font=verysmallfont, fill="white")  # subtopic
        if 'CHECK2' in topic and topic['CHECK2'] is not None:
            if toprint:
                right_text(y, topic['CHECK2'], font=verysmallfont, fill="yellow", offset=topic_right_offset)
        y += VERYSMALL
    if 'TASK3' in topic and topic['TASK3'] is not None:  # subtopic3
        y += subtopic_offset
        if toprint:
            draw.text((xpos_sub, y), topic['TASK3'], font=verysmallfont, fill="white")  # subtopic
        if 'CHECK3' in topic and topic['CHECK3'] is not None:
            if toprint:
                right_text(y, topic['CHECK3'], font=verysmallfont, fill="yellow", offset=topic_right_offset)
        y += VERYSMALL
    if highlighted:  # draw frame around whole topic
        if toprint:
            draw.rounded_rectangle([0, ypos - 1, sizex-1, y + 1], width=1, radius=3, outline="white")
    return y + topic_offset


def checklist(checklist_name, checklist_items, current_index, last_list):
    checklist_y = {'from': SMALL + 8, 'to': sizey - VERYSMALL - 6}
    global top_index

    centered_text(0, checklist_name, smallfont, fill="yellow")
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
        bottom_line(left, "Mode", "Checked")
    else:
        bottom_line(left, "NxtList", "Check")
