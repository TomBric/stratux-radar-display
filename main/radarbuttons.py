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

from globals import rlog
from gpiozero import Button
from gpiozero.exc import GPIOZeroError, GPIODeviceError
import threading   # for flask server in case of button api
from flask import Flask, jsonify, render_template
from flask_wtf import FlaskForm, CSRFProtect
from wtforms.fields import *
from flask_bootstrap import Bootstrap5, SwitchField
import os

btn = None   # will be set in init
gear_down_btn = None   # will be set ini int

# global constants
HOLD_TIME = 0.8 # time to trigger the hold activity if one button is pressed longer
GEAR_HOLD_TIME = 0.3   # time until gear is indicated to be down
BOUNCE_TIME = 0.05
LEFT = 26
MIDDLE = 20
RIGHT = 21
GEAR_DOWN = 19

# Flask server for button api
app = Flask(__name__, template_folder='radar-web/templates')
app.secret_key = 'radar-api'
# Bootstrap configuration
app.config['BOOTSTRAP_SERVE_LOCAL'] = True      # use local instances of css etc.
app.config['BOOTSTRAP_USE_MINIFIED'] = True
app.config['BOOTSTRAP_BTN_STYLE'] = 'primary'
app.config['BOOTSTRAP_BTN_SIZE'] = 'sm'
app.config['WTF_CSRF_ENABLED'] = False    # to enable api call without csrf token
bootstrap = Bootstrap5(app)
# csrf = CSRFProtect(app)


button_api_active = False
last_api_input = 0, 0


class ApiForm(FlaskForm):
    left_short =   SubmitField('  Left Short ')
    left_long =    SubmitField('  Left Long  ')
    middle_short = SubmitField(' Middle Short')
    middle_long =  SubmitField(' Middle Long ')
    right_short =  SubmitField(' Right Short ')
    right_long =   SubmitField(' Right Long  ')

# section for button api, only used when option "-api" is set
# to trigger interactively you can use CURL
# e.g. to trigger middle-long:
# curl -s -o /dev/null -X POST -H "Content-Type: application/x-www-form-urlencoded" -d "middle_long=Middle Long" http://192.168.10.15/api
# e.g. to trigger right-short:
# curl -s -o /dev/null -X POST -H "Content-Type: application/x-www-form-urlencoded" -d "right_short=Right Short" http://192.168.10.15/api
@app.route('/api', methods=['GET', 'POST'])
def api():
    global last_api_input

    api_form = ApiForm()
    if api_form.validate_on_submit() is True:  # POST request
        if api_form.left_short.data is True:
            last_api_input = 1, 0
        elif api_form.left_long.data is True:
            last_api_input = 2, 0
        elif api_form.middle_short.data is True:
            last_api_input = 1, 1
        elif api_form.middle_long.data is True:
            last_api_input = 2, 1
        elif api_form.right_short.data is True:
            last_api_input = 1, 2
        elif api_form.right_long.data is True:
            last_api_input = 2, 2
        else:
            last_api_input = 0, 0
    rlog.debug(f"API: api_input={last_api_input}")
    return render_template('api.html', api_form=api_form)


def read_api_input():
    global last_api_input

    if not button_api_active:
        return 0, 0
    else:
        ret = last_api_input
        last_api_input = 0, 0
        return ret

def run_flask():
    global button_api_active

    button_api_active = True
    rlog.debug(f"radar-buttons: sudo systemctl start nginx")
    ret = os.system('sudo systemctl start nginx') # just in case it has been stopped before
    if ret != 0:
        rlog.error(f"radarbuttons: Failed to start nginx, return code: {ret}")
    else:
        rlog.debug(f"radarbuttons: starting flask app")
    app.run(debug=False, use_reloader=False)



class RadarButton:
    def __init__(self,gpio_number):
        self.btn = Button(gpio_number, bounce_time=BOUNCE_TIME, hold_time=HOLD_TIME)
        self.short = False
        self.long = False
        self.already_triggered = False
        self.btn.when_released = self.released
        self.btn.when_held = self.held

    def released(self):
        if not self.already_triggered:
            self.short = True
        else:
            self.already_triggered = False

    def held(self):
        self.long = True
        self.already_triggered = True

    def check_button(self):
        if self.long:
            self.long = False
            return 2
        if self.short:
            self.short = False
            return 1
        return 0


def init(button_api):
    global btn
    global button_api_active

    try:
        btn = [RadarButton(LEFT), RadarButton(MIDDLE), RadarButton(RIGHT)]
    except:
        rlog.debug("ERROR: GPIO-Pins busy! No input possible. Please clarify!")
        return False  # indicate errors
    rlog.debug("Radarbuttons: Initialized.")
    if button_api: # start an api for the buttons
        button_api_active = True
        rlog.debug("Radarbuttons UI: Starting button API via flask")
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.daemon = True # to stop the thread when the main program stops
        flask_thread.start()
    return True    # indicate everything is fine


def check_buttons():  # returns 0=nothing 1=short press 2=long press and returns Button (0,1,2)
    for index, but in enumerate(btn):
        stat = but.check_button()
        if stat > 0:
            rlog.debug("Button press: button {0} presstime {1} (1=short, 2=long)".format(index, stat))
            return stat, index
    # nothing pressed, now also check button_api
    return read_api_input()


def gear_is_down():
    return gear_down_btn.is_held

def init_gear_indicator():
    global gear_down_btn

    try:
        gear_down_btn = Button(GEAR_DOWN, bounce_time=BOUNCE_TIME, hold_time=GEAR_HOLD_TIME)
    except:
        rlog.debug("Radarbuttons ERROR: GPIO-Pin {0} for gear down indication busy! Please clarify!".format(GEAR_DOWN))
        return False
    rlog.debug("Radarbuttons: Gear down indicator on GPIO{0} initialized.".format(GEAR_DOWN))
    return True