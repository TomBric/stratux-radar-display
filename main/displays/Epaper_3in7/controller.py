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

import logging
from . import epd3in7
from PIL import Image, ImageDraw, ImageFont
import math
import time
from pathlib import Path

# global constants
VERYLARGE = 48    # timer
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
azerox = 140  # zero for analogue meter
azeroy = 140
asize = 140
msize = 15  # size of markings
m_marks = ((180, -3), (202.5, -2), (225, -1), (247.5, 0), (270, 1), (292.5, 2), (315, 3), (337.5, 4), (0, 5))
# compass
compass_aircraft = None   # image of aircraft for compass-display
mask = None
cdraw = None
cmsize = 16        # length of compass marks
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


def init():
    global sizex
    global sizey
    global zerox
    global zeroy
    global ah_zerox
    global ah_zeroy
    global max_pixel
    global verylargefont
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
    zeroy = 200    # not centered
    ah_zeroy = sizey / 2   # zero line for ahrs
    ah_zerox = sizex / 2
    max_pixel = 400
    verylargefont = make_font("Font.ttc", VERYLARGE)
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
    logging.info("Measured Display Refresh Time: " + str(round(display_refresh, 3)) + " seconds")
    # compass
    pic_path = str(Path(__file__).resolve().parent.joinpath('plane-white-128x128.bmp'))
    compass_aircraft = Image.open(pic_path)
    compass_aircraft.putalpha(255)   # set transparency mask
    mask = Image.new('1', (LARGE * 2, LARGE * 2))
    cdraw = ImageDraw.Draw(mask)
    return draw, max_pixel, zerox, zeroy, display_refresh


def cleanup():
    global device

    device.init(0)
    device.Clear(0xFF, 0)
    device.sleep()
    device.Dev_exit()
    logging.debug("Epaper cleaned up.")


def refresh():
    global device

    device.Clear(0xFF, 0)  # necessary to overwrite everything
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
    logopath = str(Path(__file__).resolve().parent.joinpath('stratux-logo-192x192.bmp'))
    logo = Image.open(logopath)
    draw.bitmap((zerox-192/2, 0), logo, fill="black")
    versionstr = "Epaper-Radar " + version
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
    tsize = draw.textsize(t, largefont)
    if tsize[0] + x + 4 * AIRCRAFT_SIZE - 2 > sizex:
        # would draw text outside, move to the left
        tposition = (x - 4 * AIRCRAFT_SIZE - tsize[0], int(y - tsize[1] / 2))
    else:
        tposition = (x + 4 * AIRCRAFT_SIZE + 1, int(y - tsize[1] / 2))
    draw.rectangle((tposition, (tposition[0] + tsize[0], tposition[1] + LARGE)), fill="white")
    draw.text(tposition, t, font=largefont, fill="black")
    if tail is not None:
        tsize = draw.textsize(tail, verysmallfont)
        draw.rectangle((tposition[0], tposition[1]+LARGE, tposition[0]+tsize[0],
                        tposition[1]+LARGE+VERYSMALL), fill="white")
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
              gps_quality, gps_h_accuracy):
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
    draw.text((5, SMALL+10), t, font=verysmallfont, fill="black")

    t = "FL"+str(round(ownalt / 100))
    textsize = draw.textsize(t, verysmallfont)
    draw.text((sizex - textsize[0] - 5, SMALL+10), t, font=verysmallfont, fill="black")

    t = str(altdifference) + " ft"
    textsize = draw.textsize(t, smallfont)
    draw.text((sizex - textsize[0] - 5, 1), t, font=smallfont, fill="black", align="right")

    text = str(course) + '°'
    centered_text(draw, 1, text, smallfont, fill="black")

    if not gpsconnected:
        centered_text(draw, 70, "No GPS", smallfont, fill="black")
    if not connected:
        centered_text(draw, 30, "No Connection!", smallfont, fill="black")

    if bt_devices > 0:
        if sound_active:
            t = "\uf293"  # bluetooth symbol
        else:
            t = "\uf1f6"  # bell off symbol
        textsize = draw.textsize(t, awesomefont)
        draw.text((sizex - textsize[0] - 5, sizey - SMALL), t, font=awesomefont, fill="black")


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


def gmeter(draw, current, maxg, ming, error_message):
    for m in m_marks:
        s = math.sin(math.radians(m[0]+90))
        c = math.cos(math.radians(m[0]+90))
        draw.line((azerox-asize*c, azeroy-asize*s, azerox-(asize-msize)*c, azeroy-(asize-msize)*s),
                  fill="black", width=4)
        draw.text((azerox-(asize-msize-SMALL/2)*c, azeroy-(asize-msize-SMALL/2)*s-SMALL/2),
                  str(m[1]), font=smallfont, fill="black")
    draw.arc((0, 0, azerox*2, azeroy*2), 90, 270, width=6, fill="black")
    draw.ellipse((azerox-10, azeroy-10, azerox+10, azeroy+10), outline="black", fill="black", width=1)
    gval = (current-1.0)*22.5
    s = math.sin(math.radians(gval))
    c = math.cos(math.radians(gval))
    draw.line((azerox-(asize-msize-3)*c, azeroy-(asize-msize-3)*s, azerox, azeroy), fill="black", width=8)

    draw.text((zerox-30, 0), "G-Meter", font=verylargefont, fill="black")
    draw.text((zerox-30, 88), "max", font=smallfont, fill="black")
    right_text(draw, 85, "{:+1.2f}".format(maxg), largefont, fill="black")
    if error_message is None:
        draw.text((zerox-30, 138), "current", font=smallfont, fill="black")
        right_text(draw, 126, "{:+1.2f}".format(current), verylargefont, fill="black")
    else:
        draw.text((zerox-30, 138), error_message, font=largefont, fill="black")
    draw.text((zerox-30, 188), "min", font=smallfont, fill="black")
    right_text(draw, 185, "{:+1.2f}".format(ming), largefont, fill="black")

    right = "Reset"
    middle = "Mode"
    textsize = draw.textsize(right, smallfont)
    draw.text((sizex-textsize[0]-8, sizey-SMALL-3), right, font=smallfont, fill="black", align="right")
    centered_text(draw, sizey-SMALL-3, middle, smallfont, fill="black")


def compass(draw, heading, error_message):
    global epaper_image
    global mask
    global cdraw

    czerox = sizex / 2
    czeroy = sizey / 2
    csize = sizey / 2  # radius of compass rose

    draw.ellipse((sizex/2-csize, 0, sizex/2+csize-1, sizey - 1), outline="black", fill="white", width=4)
    draw.bitmap((zerox - 60, 80), compass_aircraft, fill="black")
    # epaper_image.paste("black", (round(zerox) - 60, 60), compass_aircraft)
    draw.line((czerox, 10, czerox, 30), fill="black", width=3)
    text = str(heading) + '°'
    textsize = draw.textsize(text, smallfont)
    draw.text((sizex - textsize[0], sizey - textsize[1]), text, font=smallfont, fill="black", align="right")
    for m in range(0, 360, 10):
        s = math.sin(math.radians(m - heading + 90))
        c = math.cos(math.radians(m - heading + 90))
        draw.line((czerox - (csize - 1) * c, czeroy - (csize - 1) * s, czerox - (csize - cmsize) * c,
                   czeroy - (csize - cmsize) * s),
                  fill="black", width=2)
        if m % 30 == 0:
            color = "black"
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
                color = "black"
            cdraw.rectangle((0, 0, LARGE * 2, LARGE * 2), fill="black")
            w, h = largefont.getsize(mark)
            cdraw.text(((LARGE * 2 - w) / 2, (LARGE * 2 - h) / 2), mark, 1, font=largefont)
            rotmask = mask.rotate(-m + heading, expand=False)
            center = (czerox - (csize - cmsize - LARGE / 2) * c, czeroy - (csize - cmsize - LARGE / 2) * s)
            epaper_image.paste(color, (round(center[0] - LARGE), round(center[1] - LARGE)), rotmask)
    if error_message is not None:
        centered_text(draw, 120, error_message, largefont, fill="black")


def shutdown(draw, countdown):
    message = "Shutdown "
    centered_text(draw, 10, message, largefont, fill="black")
    message = "in " + str(countdown) + " seonds!"
    centered_text(draw, 40, message, largefont, fill="black")
    message = "Press any button"
    centered_text(draw, 110, message, smallfont, fill="black")
    message = "to cancel ..."
    centered_text(draw, 130, message, smallfont, fill="black")


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
    textsize = draw.textsize(right_text, smallfont)
    draw.text((sizex - textsize[0] - 8, sizey - SMALL - 3), right_text, font=smallfont, fill="black", align="right")
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
    textsize = draw.textsize(right, smallfont)
    draw.text((sizex - textsize[0] - 8, sizey - SMALL - 3), right, font=smallfont, fill="black", align="right")
    centered_text(draw, sizey - SMALL - 8, middle, smallfont, fill="black")
