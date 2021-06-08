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
from pathlib import Path
from PIL import Image, ImageFont, ImageDraw
from . import radar_opts

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
cmsize = 10        # length of compass marks
# end device globals


def posn(angle, arm_length):
    dx = round(math.cos(math.radians(angle)) * arm_length)
    dy = round(math.sin(math.radians(angle)) * arm_length)
    return dx, dy


def make_font(name, size):
    font_path = str(Path(__file__).resolve().parent.joinpath('fonts', name))
    return ImageFont.truetype(font_path, size)


def init():
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

    config_path = str(Path(__file__).resolve().parent.joinpath('ssd1351.conf'))
    device = radar_opts.get_device(['-f', config_path])
    image = Image.new(device.mode, device.size)
    draw = ImageDraw.Draw(image)
    sizex = device.width
    sizey = device.height
    zerox = sizex / 2
    zeroy = sizey / 2
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
    return draw, sizex, zerox, zeroy, display_refresh


def cleanup():
    device.cleanup()


def centered_text(draw, y, text, font, fill):
    ts = draw.textsize(text, font)
    draw.text((zerox - ts[0] / 2, y), text, font=font, fill=fill)


def right_text(draw, y, text, font, fill):
    ts = draw.textsize(text, font)
    draw.text((sizex - ts[0], y), text, font=font, fill=fill)


def display():
    device.display(image)


def is_busy():
    # oled is never busy, no refresh
    return False


def next_arcposition(old_arcposition):
    # defines next position of height indicator on circle. Can be used to exclude several ranges or
    # be used to define the next angle on the circle
    return (old_arcposition + 210) % 360


def clear(draw):
    draw.rectangle((0, 0, sizex - 1, sizey - 1), fill="black")


def refresh():
    pass  # nothing to do for Oled, does not need a refresh function


def startup(draw, version, target_ip, seconds):
    logopath = str(Path(__file__).resolve().parent.joinpath('stratux-logo-64x64.bmp'))
    logo = Image.open(logopath)
    draw.rectangle(((0, 0), (sizex, 64)), fill="blue")
    draw.bitmap((zerox - 32, 0), logo, fill="white")
    centered_text(draw, 64, "OledRadar "+version, largefont, fill="white")
    centered_text(draw, sizey - 3 * SMALL, "Connecting to", smallfont, fill="white")
    centered_text(draw, sizey - 2*SMALL, target_ip, smallfont, fill="white")
    display()
    time.sleep(seconds)


def aircraft(draw, x, y, direction, height, vspeed, nspeed_length, tail):
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
    tsize = draw.textsize(t, largefont)
    if tsize[0] + x + 4 * AIRCRAFT_SIZE - 2 > sizex:
        # would draw text outside, move to the left
        tposition = (x - 4 * AIRCRAFT_SIZE - tsize[0], int(y - tsize[1] / 2))
    else:
        tposition = (x + 4 * AIRCRAFT_SIZE + 1, int(y - tsize[1] / 2))
    draw.rectangle((tposition, (tposition[0] + tsize[0], tposition[1] + tsize[1])), fill="black")
    draw.text(tposition, t, font=largefont, fill="white")


def modesaircraft(draw, radius, height, arcposition, vspeed, tail):
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
    tsize = draw.textsize(t, largefont)
    tposition = (64 + arctext[0] - tsize[0] / 2, 64 + arctext[1] - tsize[1] / 2)
    draw.rectangle((tposition, (tposition[0] + tsize[0], tposition[1] + tsize[1])), fill="black")
    draw.text(tposition, t, font=largefont, fill="white")


def situation(draw, connected, gpsconnected, ownalt, course, range, altdifference, bt_devices, sound_active,
              gps_quality, gps_h_accuracy, optical_alive):
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
    textsize = draw.textsize(t, smallfont)
    draw.text((sizex - textsize[0], 0), t, font=smallfont, fill="floralwhite", align="right")

    text = "ft"
    textsize = draw.textsize(text, smallfont)
    draw.text((sizex - textsize[0], SMALL), text, font=verysmallfont, fill="floralwhite", align="right")

    text = str(course) + '°'
    textsize = draw.textsize(text, smallfont)
    draw.text((sizex - textsize[0], sizey - textsize[1]), text, font=smallfont, fill="floralwhite", align="right")

    if bt_devices > 0:
        if sound_active:
            btcolor = "blue"
            text = '\uf293'  # bluetooth symbol + no
        else:
            btcolor = "red"
            text = '\uf1f6'  # bell off symbol
        textsize = draw.textsize(text, webfont)
        draw.text((sizex - textsize[0], sizey - 2 * SMALL), text, font=webfont, fill=btcolor, align="right")

    if not gpsconnected:
        centered_text(draw, 0, "No GPS", smallfont, fill="red")
    if not connected:
        centered_text(draw, zeroy, "No Connection!", smallfont, fill="red")


def timer(draw, utctime, stoptime, laptime, laptime_head, left_text, middle_text, right_text, timer_runs):
    draw.text((0, 0), "UTC", font=smallfont, fill="cyan")
    centered_text(draw, SMALL, utctime, verylargefont, fill="yellow")
    draw.text((0, SMALL + VERYLARGE), "Timer", font=smallfont, fill="cyan")
    if timer_runs:
        color = "lavender"
    else:
        color = "orangered"
    centered_text(draw, 2 * SMALL + VERYLARGE, stoptime, verylargefont, fill=color)
    draw.text((0, 2 * SMALL + 2 * VERYLARGE), laptime_head, font=smallfont, fill="cyan")
    if laptime_head == "Laptimer":
        centered_text(draw, 3 * SMALL + 2 * VERYLARGE, laptime, verylargefont, fill="powderblue")
    else:
        centered_text(draw, 3 * SMALL + 2 * VERYLARGE, laptime, verylargefont, fill="magenta")

    draw.text((0, sizey - SMALL - 3), left_text, font=smallfont, fill="green")
    textsize = draw.textsize(right_text, smallfont)
    draw.text((sizex - textsize[0], sizey - SMALL - 3), right_text, font=smallfont, fill="green", align="right")
    centered_text(draw, sizey - SMALL - 3, middle_text, smallfont, fill="green")


def gmeter(draw, current, maxg, ming, error_message):
    centered_text(draw, 0, "G-Meter", largefont, fill="yellow")
    draw.text((0, 36), "max", font=smallfont, fill="cyan")
    right_text(draw, 30, "{:+1.2f}".format(maxg), largefont, fill="magenta")
    if error_message is None:
        draw.text((0, 57), "current", font=smallfont, fill="cyan")
        right_text(draw, 48, "{:+1.2f}".format(current), verylargefont, fill="white")
    else:
        centered_text(draw, 57, error_message, largefont, fill="red")
    draw.text((0, 80), "min", font=smallfont, fill="cyan")
    right_text(draw, 74, "{:+1.2f}".format(ming), largefont, fill="magenta")

    right = "Reset"
    textsize = draw.textsize(right, smallfont)
    draw.text((sizex - textsize[0], sizey - SMALL - 3), right, font=smallfont, fill="green", align="right")
    middle = "Mode"
    centered_text(draw, sizey - SMALL - 3, middle, smallfont, fill="green")


def compass(draw, heading, error_message):
    global image
    global mask
    global cdraw

    csize = sizex/2   # radius of compass rose

    draw.ellipse((0, 0, sizex-1, sizey-1), outline="white", fill="black", width=2)
    image.paste(compass_aircraft, (round(zerox) - 30, 30))
    draw.line((zerox, 10, zerox, 30), fill="white", width=1)
    text = str(heading) + '°'
    textsize = draw.textsize(text, smallfont)
    draw.text((sizex - textsize[0], sizey - textsize[1]), text, font=smallfont, fill="floralwhite", align="right")
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
            w, h = draw.textsize(mark, largefont)
            cdraw.text(((LARGE*2-w)/2, (LARGE*2-h)/2), mark, 1, font=largefont)
            rotmask = mask.rotate(-m+heading, expand=False)
            center = (zerox - (csize - cmsize - LARGE / 2) * c, zeroy - (csize - cmsize - LARGE / 2) * s)
            image.paste(color, (round(center[0]-LARGE), round(center[1]-LARGE)), rotmask)
    if error_message is not None:
        centered_text(draw, 57, error_message, largefont, fill="red")


def vsi(draw, vertical_speed, flight_level, gps_speed, gps_course, gps_altitude, vertical_max, vertical_min,
        error_message):
    csize = sizex / 2  # radius of vsi
    vmsize_n = 8
    vmsize_l = 14

    draw.arc((zerox - csize, 0, zerox + csize - 1, sizey - 1), 10, 350, fill="white", width=2)
    draw.text((12, zeroy - VERYSMALL - 12), "up", font=verysmallfont, fill="white", align="left")
    draw.text((12, zeroy + 12), "dn", font=verysmallfont, fill="white", align="left")
    middle_text = "Vert Spd"
    ts = draw.textsize(middle_text, verysmallfont)
    draw.text((zerox - ts[0] / 2, zeroy - ts[1] - 10), middle_text, font=verysmallfont, fill="white", align="left")
    middle_text = "100 ft/min"
    ts = draw.textsize(middle_text, verysmallfont)
    draw.text((zerox - ts[0] / 2, zeroy + 10), middle_text, font=verysmallfont, fill="white", align="left")

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
            w, h = draw.textsize(mark, largefont)
            if m != 2000 and m != -2000:
                center = (zerox-(csize-1-vmsize_l-LARGE/2) * c, zeroy-(csize-5-vmsize_l-LARGE/2) * s)
                draw.text((center[0] - w / 2, center[1] - h / 2), mark, fill="white", font=largefont)
            if m == 2000:  # put 2 in the middle at 180 degrees
                draw.text((zerox + (csize - 1 - vmsize_l - LARGE / 2) - w / 2, zeroy - 1 - h / 2), mark, fill="white",
                          font=largefont)

    if error_message is not None:
        centered_text(draw, 30, error_message, largefont, fill="red")

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


def shutdown(draw, countdown, shutdownmode):
    message = ""
    if shutdownmode == 0:   # shutdown stratux + display
        message = "Shutdown all"
    elif shutdownmode == 1:
        message = "Shtdwn displ"
    elif shutdownmode == 2:
        message = "Reboot"
    centered_text(draw, 10, message, largefont, fill="white")
    message = "in " + str(countdown) + " seonds!"
    centered_text(draw, 30, message, largefont, fill="white")
    message = "Left to cancel ..."
    centered_text(draw, 60, message, smallfont, fill="white")
    message = "Middle display only ..."
    centered_text(draw, 75, message, smallfont, fill="white")
    message = "Right for reboot all ..."
    centered_text(draw, 90, message, smallfont, fill="white")

    left_text = "Canc"
    middle_text = "Displ"
    right_text = "Rebo"
    draw.text((0, sizey - SMALL - 3), left_text, font=smallfont, fill="green")
    textsize = draw.textsize(right_text, smallfont)
    draw.text((sizex - textsize[0], sizey - SMALL - 3), right_text, font=smallfont, fill="green", align="right")
    centered_text(draw, sizey - SMALL - 3, middle_text, smallfont, fill="green")


def rollmarks(draw, roll):
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


def slip(draw, slipskid):
    slipsize = 5
    slipscale = 3
    if slipskid < -10:
        slipskid = -10
    elif slipskid > 10:
        slipskid = 10

    draw.rectangle((zerox - 40, device.height - slipsize * 2, zerox + 40, device.height - 1), fill="black")
    draw.ellipse((zerox - slipskid * slipscale - slipsize, device.height - slipsize * 2,
                  zerox - slipskid * slipscale + slipsize, device.height - 1), fill="white")


def ahrs(draw, pitch, roll, heading, slipskid, error_message):
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
    rollmarks(draw, roll)
    # slip indicator
    slip(draw, slipskid)

    # infotext = "P:" + str(pitch) + " R:" + str(roll)
    if error_message:
        centered_text(draw, 30, error_message, smallfont, fill="red")


def text_screen(draw, headline, subline, text, left, middle, right):
    centered_text(draw, 0, headline, largefont, fill="yellow")
    txt_starty = LARGE
    if subline is not None:
        centered_text(draw, LARGE, subline, smallfont, fill="yellow")
        txt_starty += LARGE
    draw.text((0, txt_starty), text, font=smallfont, fill="white")
    draw.text((0, sizey - SMALL - 3), left, font=smallfont, fill="green")
    textsize = draw.textsize(right, smallfont)
    draw.text((sizex - textsize[0], sizey - SMALL - 3), right, font=smallfont, fill="green", align="right")
    centered_text(draw, sizey - SMALL - 3, middle, smallfont, fill="green")


def screen_input(draw, headline, subline, text, left, middle, right, prefix, inp, suffix):
    centered_text(draw, 0, headline, largefont, fill="yellow")
    txt_starty = LARGE
    if subline is not None:
        centered_text(draw, LARGE, subline, smallfont, fill="yellow")
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
    textsize = draw.textsize(right, smallfont)
    draw.text((sizex - textsize[0], sizey - SMALL - 3), right, font=smallfont, fill="green", align="right")
    centered_text(draw, sizey - SMALL - 3, middle, smallfont, fill="green")


def bar(draw, y, text, val, max_val, yellow, red, unit=""):
    bar_start = 30
    bar_end = 100

    draw.text((0, y), text, font=verysmallfont, fill="white", align="left")
    right_val = str(int(max_val)) + unit
    textsize = draw.textsize(right_val, verysmallfont)
    draw.text((sizex - textsize[0], y), right_val, font=verysmallfont, fill="white", align="right")
    draw.rounded_rectangle([bar_start-2, y-2, bar_end+2, y+VERYSMALL+2], radius=3, fill=None, outline="white", width=1)
    if red == 0:
        color = "DimGray"
    elif val >= red:
        color = "red"
    elif val >= yellow:
        color = "DarkOrange"
    else:
        color = "green"
    if max_val != 0:
        xval = bar_start + (bar_end - bar_start) * val / max_val
    else:
        xval = 0
    draw.rectangle([bar_start, y, xval, y+VERYSMALL], fill=color, outline=None)
    t = str(val)
    textsize = draw.textsize(t, verysmallfont)
    draw.text(((bar_end-bar_start)/2+bar_start-textsize[0]/2, y), t, font=verysmallfont, fill="white")
    return y+VERYSMALL+5

def round_text(draw,x, y, text, color):
    ts = draw.textsize(text, verysmallfont)
    draw.rounded_rectangle([x-2, y-2, x+ts[0]+2, y+ts[1]+2], radius=4, fill=color, outline="white")
    draw.text((x,y), text, font=verysmallfont, fill="white")
    return x+ts[0]+2

def stratux(draw, stat, altitude, gps_alt):
    starty = 0
    centered_text(draw, 0, "Stratux " + stat['version'], smallfont, fill="yellow")
    starty += SMALL+8
    starty = bar(draw, starty, "1090", stat['ES_messages_last_minute'], stat['ES_messages_max'], 0, 0)
    if stat['OGN_connected']:
        starty = bar(draw, starty, "OGN", stat['OGN_messages_last_minute'], stat['OGN_messages_max'], 0, 0)
        noise_text = "noise= " + str(stat['OGN_noise_db']) + "@" + str(stat['OGN_gain_db']) + " dB"
        centered_text(draw, starty, noise_text, verysmallfont, fill="white")
        starty += VERYSMALL
    if stat['UATRadio_connected']:
        starty = bar(draw, starty, "UAT", stat['UAT_messages_last_minute'], stat['UAT_messages_max'], 0, 0)
    starty += 6
    if stat['CPUTemp'] > -300:   #  -300 means no value available
        starty = bar(draw, starty, "Temp", round(stat['CPUTemp'],1) , round(stat['CPUTempMax'],0), 70, 80, "°C")
        starty += 3
    # GPS
    draw.text((0, starty), "GPS", font=verysmallfont, fill="white")
    draw.rounded_rectangle([35, starty, 55, starty + VERYSMALL], radius=4, fill="green", outline=None)
    draw.rounded_rectangle([55, starty, 75, starty + VERYSMALL], radius=4, fill="DarkOrange", outline=None)
    draw.rounded_rectangle([75, starty, 95, starty + VERYSMALL], radius=4, fill="red", outline=None)
    t = str(stat['GPS_satellites_locked'])
    textsize = draw.textsize(t, verysmallfont)
    draw.text((48-textsize[0]/2, starty), t, font=verysmallfont, fill="white", align="middle")
    t = str(stat['GPS_satellites_seen'])
    textsize = draw.textsize(t, verysmallfont)
    draw.text((67-textsize[0]/2, starty), t, font=verysmallfont, fill="white", align="middle")
    t = str(stat['GPS_satellites_tracked'])
    textsize = draw.textsize(t, verysmallfont)
    draw.text((87-textsize[0]/2, starty), t, font=verysmallfont, fill="white", align="middle")
    if stat['GPS_position_accuracy'] < 19999:
        gps = str(round(stat['GPS_position_accuracy'],1)) + "m"
    else:
        gps = "NoFix"
    textsize = draw.textsize(gps, verysmallfont)
    draw.text((sizex - textsize[0], starty), gps, font=verysmallfont, fill="white")
    starty += VERYSMALL+5

    fl = '{:3.0f}'.format(round(altitude) / 100)
    x = round_text(draw, 3, starty, fl, "none")
    alt = '{:5.0f}'.format(gps_alt)
    x = round_text(x, starty, alt, None)
    if stat['IMUConnected']:
        col = "green"
    else:
        col = "red"
    x = round_text(draw, x, starty, "IMU", col)
    if stat['BMPConnected']:
        col = "green"
    else:
        col = "red"
    x = round_text(draw, x, starty, "BMP", col)

    centered_text(draw, sizey - SMALL - 3, "Mode", smallfont, fill="green")
