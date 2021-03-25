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
ahrs_draw = None
roll_posmarks = (-90, -60, -30, -20, -10, 0, 10, 20, 30, 60, 90)
pitch_posmarks = (-30, -20, -10, 10, 20, 30)
compass_aircraft = None   # image of aircraft for compass-display


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
    pic_path = str(Path(__file__).resolve().parent.joinpath('plane-white-64x64.bmp'))
    compass_aircraft = Image.open(pic_path).convert("RGBA")
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
              gps_quality, gps_h_accuracy):
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

    cimage = Image.new(device.mode, (SMALL*2, SMALL*2))  # larger to make sure rotated characters still fit
    cdraw = ImageDraw.Draw(cimage)
    csize = sizex/2   # radius of compass rose
    cmsize = 7        # length of compass marks

    draw.ellipse((0, 0, sizex-1, sizey-1), outline="white", fill="black", width=2)
    image.paste(compass_aircraft, (round(zerox) - 30, 30))
    draw.line((zerox, 0, zerox, 30), fill="white", width=1)
    draw.polygon((zerox, 12, zerox - 6, 0, zerox + 6, 0), fill="white")
    for m in range(0, 360, 10):
        s = math.sin(math.radians(heading + m))
        c = math.cos(math.radians(heading + m))
        draw.line((zerox - csize * c, zeroy - csize * s, zerox - (csize - cmsize) * c, zeroy - (csize - cmsize) * s),
                  fill="white", width=1)
        if m % 30 == 0:
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
            cdraw.rectangle((0,0,SMALL*2,SMALL*2),fill="black")
            cdraw.text((SMALL/2, SMALL/2), mark, font=smallfont, fill="white")
            rotim = cimage.rotate(-heading-m+90)
            t = math.tan(math.radians(heading+m))
            center = (zerox - (csize - cmsize - SMALL / 2) * c, zeroy - (csize - cmsize - SMALL / 2) * s)
            # image.paste(rotim, (round(center[0]-t*LARGE), round(center[1]-LARGE/t)))
            image.paste(rotim, (round(center[0]-SMALL), round(center[1])-SMALL))
    if error_message is not None:
        centered_text(draw, 57, error_message, largefont, fill="red")


def shutdown(draw, countdown):
    message = "Shutdown "
    centered_text(draw, 10, message, largefont, fill="white")
    message = "in " + str(countdown) + " seonds!"
    centered_text(draw, 30, message, largefont, fill="white")
    message = "Press any button"
    centered_text(draw, 60, message, smallfont, fill="white")
    message = "to cancel ..."
    centered_text(draw, 80, message, smallfont, fill="white")


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
