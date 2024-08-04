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

import argparse
import logging
import os
import signal
import threading

from flask import Flask, render_template, request, flash, redirect, url_for
from markupsafe import Markup
from flask_wtf import FlaskForm, CSRFProtect
from wtforms.validators import DataRequired, Length, Regexp
from wtforms.fields import *
from flask_bootstrap import Bootstrap5, SwitchField

RADAR_WEB_VERSION = "0.5"

app = Flask(__name__)
app.secret_key = 'radar-web-51Hgfw'

# set default button sytle and size, will be overwritten by macro parameters
app.config['BOOTSTRAP_BTN_STYLE'] = 'primary'
app.config['BOOTSTRAP_BTN_SIZE'] = 'md'

bootstrap = Bootstrap5(app)
csrf = CSRFProtect(app)

rlog = None  # radar specific logger
watchdog = None  # watchdog to shut down


class Watchdog():
    def __init__(self, timeout=180):
        self.timeout = timeout
        self._t = None

    def do_expire(self):
        rlog.debug(f'radar-web: watchdog timeout expired! Stopping flask-app. ')
        os.kill(os.getpid(),signal.SIGINT)

    def _expire(self):
        rlog.debug(f'radar-web: watchdog timeout expired! ')
        self.do_expire()

    def start(self):
        if self.timeout > 0 and self._t is None:
            self._t = threading.Timer(self.timeout, self._expire)
            self._t.start()

    def stop(self):
        if self._t is not None:
            self._t.cancel()
            self._t = None

    def refresh(self):
        if self._t is not None:
             self.stop()
             self.start()


def logging_init():
    global rlog
    logging.basicConfig(level=logging.INFO, format='%(asctime)-15s > %(message)s')
    rlog = logging.getLogger('stratux-radar-web-log')


class RadarForm(FlaskForm):
    display = RadioField(' ',choices=[('NoDisplay', 'No display'), ('Oled_1in5', 'Oled 1.5 inch'), ('Epaper_1in54', 'Epaper display 1.54 inch'), ('Epaper_3in7', 'Epaper display 3.7 inch')], default='Epaper_3in7')

    radar = SwitchField('Radar', description=' ', default=True)
    radar_seq = IntegerField(label='', default=1)
    timer = SwitchField('Timer', default=True)
    timer_seq = IntegerField('', default=2)
    ahrs = SwitchField('Artificial horizon', default=True)
    ahrs_seq = IntegerField('', default=3)
    gmeter = SwitchField('G-Meter', default=True)
    gmeter_seq = IntegerField('', default=4)
    compass = SwitchField('GPS based compass', default=True)
    compass_seq = IntegerField('', default=5)
    vspeed = SwitchField('Vertical speed', default=True)
    vspeed_seq = IntegerField('', default=6)
    flogs = SwitchField('Flight logs', default=True)
    flogs_seq = IntegerField('', default=7)
    gps_dist = SwitchField('GPS distance measuring', default=False)
    gps_dist_seq = IntegerField('', default=8)
    status = SwitchField('Display status', default=True)
    status_seq = IntegerField('', default=9)
    stratux = SwitchField('Stratux status', default=True)
    stratux_seq = IntegerField('', default=10)
    checklist = SwitchField('Checklists status', default=False)
    checklist_seq = IntegerField('', default=11)

    save_restart = SubmitField('Save and restart radar')
    save = SubmitField('Save configuration only')
    restart = SubmitField('Restart radar only')
    cancel = SubmitField('Exit without saving')


@app.route('/')
@app.route('/', methods=['GET', 'POST'])
def index():
    watchdog.refresh()
    radar_form = RadarForm()
    if radar_form.validate_on_submit():
        return redirect(url_for('result'))
    return render_template(
        'index.html',
        radar_form=radar_form
    )


@app.route('/result', methods=['GET', 'POST'])
def result():
    watchdog.refresh()
    flash(Markup('A simple success alert with <a href="#" class="alert-link">an example link</a>. Give it a click if you like.'), 'success')
    return render_template('result.html')


@app.route('/icon')
def test_icon():
    return render_template('icon.html')


@app.route('/icons')
def test_icons():
    return render_template('icons.html')


if __name__ == '__main__':
    print("Stratux Radar Web Configuration Server " + RADAR_WEB_VERSION + " running ...")
    logging_init()
    ap = argparse.ArgumentParser(description='Stratux radar web configuration')
    ap.add_argument("-t", "--timer", required=False, help="Inactivity timer after which server will shut down", default=3)
    ap.add_argument("-v", "--verbose", type=int, required=False, help="Debug level [0-1]", default=0)
    args = vars(ap.parse_args())
    flask_debug = False
    if args['verbose'] == 0:
        flask_debug = False
        rlog.setLevel(logging.INFO)
    elif args['verbose'] == 1:
        flask_debug = True
        rlog.setLevel(logging.DEBUG)  # log events without situation and aircraft
    shutdown_timer = 60 * args['timer']
    rlog.debug(f"radar-web: setting watchdog timer to {shutdown_timer} seconds")
    watchdog = Watchdog(shutdown_timer)
    watchdog.start()

    app.run(debug=flask_debug)
