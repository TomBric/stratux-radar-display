#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK
#
# BSD 3-Clause License
# Copyright (c) 2021, Thomas Breitbach
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
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import logging
import requests
import radarbuttons
import radarmodes
import threading   # for flask server in case of button api
from flask import Flask, jsonify, render_template

# status variables for state machine
display_radius = (2, 3, 5, 10, 20, 40)
height_diff = (1000, 2000, 5000, 10000, 50000)
sound_on = True

url_settings_set = ""
rlog = None
app = Flask(__name__, template_folder='radar-web/templates')


# section for button api, just used with option "-api"
@app.route('/buttonapi/<param1>/<param2>', methods=['GET'])
def get_items_with_params(param1, param2):
    # Example logic using the parameters
    result = {
        "param1": param1,
        "param2": param2,
        "message": f"Received parameters: {param1} and {param2}"
    }
    return jsonify(result)

@app.route('/api')
def api_page():
    return render_template('api_page.html')


@app.route('/')
def home():
    return "Hello, Flask!"

def run_flask():
    app.run(debug=False, use_reloader=False)


def init(url, button_api):
    global url_settings_set
    global rlog

    if not radarbuttons.init():   # error occured, e.g. gpio pins are buse
        return False
    url_settings_set = url
    rlog = logging.getLogger('stratux-radar-log')
    rlog.debug("Radar UI: Initialized POST settings to " + url_settings_set)
    if button_api: # start an api for the buttons
        rlog.debug("Radar UI: Starting button API via flask")
        # baue ein python programm, dass eine API anbietet, die die Buttons abfragt
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.start()
    return True

def communicate_limits(radarrange, threshold):
    rlog.debug("COMMUNICATE LIMITS: Radius " + str(radarrange) + " Height " + str(threshold))
    try:
        requests.post(url_settings_set, json={'RadarLimits': threshold, 'RadarRange': radarrange})
    except requests.exceptions.RequestException as e:
        rlog.debug("Posting limits exception", e)


def user_input(rrange, rlimits):   # return Nextmode, toogleSound  (Bool)
    try:
        radius = display_radius.index(rrange)
        height = height_diff.index(rlimits)
    except ValueError:   # should not occure
        radius = 2   # set standard to 5nm, if error
        height = 0   # set standard to 1000ft, if error

    btime, button = radarbuttons.check_buttons()
    if btime == 0:
        return 0, False
    if button == 0:
        if btime == 2:    # left and long
            return 3, False  # start next mode shutdown!
        else:          # left and short
            radius += 1
            if radius >= len(display_radius):
                radius = 0
            communicate_limits(display_radius[radius], height_diff[height])
    elif button == 2:
        if btime == 2:   # right and long, refresh
            return 4, False   # start next mode for display driver: refresh
        else:
            height += 1
            if height >= len(height_diff):
                height = 0
            communicate_limits(display_radius[radius], height_diff[height])
    elif button == 1:
        if btime == 2:    # middle and long
            return radarmodes.next_mode_sequence(1), False  # start next mode
        else:          # middle and short
            rlog.debug("Sound  toggled by UI")
            return 1, True
    return 1, False
