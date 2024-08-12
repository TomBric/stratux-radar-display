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
import time
# add parent path to syspath
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import arguments
import radarmodes

from flask import Flask, render_template, request, flash, redirect, url_for
from markupsafe import Markup
from flask_wtf import FlaskForm, CSRFProtect
from wtforms.validators import DataRequired, Length, Regexp, IPAddress
from wtforms.fields import *
from flask_bootstrap import Bootstrap5, SwitchField

RADAR_WEB_VERSION = "0.5"
START_RADAR_FILE = "../../image/stratux_radar.sh"
RADAR_COMMAND = "radar.py"       # command line to search in start_radar.sh
TIMEOUT = 0.5
MAX_WAIT_TIME = 10

wait = MAX_WAIT_TIME
status = '.'

app = Flask(__name__)
app.secret_key = 'radar-web-51Hgfw'

# set default button sytle and size, will be overwritten by macro parameters
app.config['BOOTSTRAP_SERVE_LOCAL'] = True      # use local instances of css etc.
app.config['BOOTSTRAP_USE_MINIFIED'] = True
app.config['BOOTSTRAP_BTN_STYLE'] = 'primary'
app.config['BOOTSTRAP_BTN_SIZE'] = 'md'

bootstrap = Bootstrap5(app)
csrf = CSRFProtect(app)

rlog = None  # radar specific logger
watchdog = None  # watchdog to shut down


class Watchdog:
    def __init__(self, timeout=180):
        self.timeout = timeout
        self._t = None

    @staticmethod
    def do_expire():
        rlog.debug(f'radar-web: watchdog timeout expired! Stopping nginx proxy. ')
        os.system('sudo systemctl stop nginx')
        rlog.debug('radar-web: watchdog timeout expired! Stopping flask-app. ')
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
    stratux_ip = StringField('IP address of Stratux', default='192.168.10.1', validators=[IPAddress()])
    display = RadioField('Display type to use',choices=[('NoDisplay', 'No display'), ('Oled_1in5', 'Oled 1.5 inch'), ('Epaper_1in54', 'Epaper display 1.54 inch'), ('Epaper_3in7', 'Epaper display 3.7 inch')], default='Epaper_3in7')

    radar = SwitchField('Radar', description=' ', default=True)
    radar_seq = IntegerField('', default=1)
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
    cowarner = SwitchField('CO warner', default=False)
    cowarner_seq = IntegerField('', default=7)
    flogs = SwitchField('Flight logs', default=True)
    flogs_seq = IntegerField('', default=8)
    gps_dist = SwitchField('GPS distance measuring', default=False)
    gps_dist_seq = IntegerField('', default=9)
    status = SwitchField('Display status', default=True)
    status_seq = IntegerField('', default=10)
    stratux = SwitchField('Stratux status', default=True)
    stratux_seq = IntegerField('', default=11)
    checklist = SwitchField('Checklists', default=False)
    checklist_seq = IntegerField('', default=12)
    checklist_filename = StringField('Checklist filename', default='checklist.xml')

    #traffic options
    registration = SwitchField('Display call sign (epaper only)', default=True)
    ground_mode = SwitchField('Ground mode, north always up', default=False)
    full_circle = SwitchField('Full circle on epaper 3.7', default=False)

    # sound options
    bluetooth = SwitchField('Bluetooth sound', default=False)
    external_sound = SwitchField('External sound output', default=False)
    sound_volume = IntegerRangeField(render_kw={'min': '0', 'max': '100'}, default=100)
    mixer = StringField('Sound mixer name', default = 'Speaker', validators=[Length(1, 40)])
    speakdistance = SwitchField('Speak distance to target', default=False)


    save_restart = SubmitField('Save and restart radar')
    save = SubmitField('Save configuration only')
    restart = SubmitField('Restart radar only')
    cancel = SubmitField('Exit without saving')

    # special options
    no_cowarner = SwitchField('Suppress activation of co sensor', default=False)
    coindicate = SwitchField('Indicate CO warning on GPIO16', default = False)
    no_flighttime = SwitchField('Suppress detection and display of flighttime', default=False)

    #ground-distance options
    groundsensor = SwitchField('Activate ground sensor via UART', default=False)
    groundbeep = SwitchField('Indicate ground distance via sound', default=False)
    gearindicate = SwitchField('Speak gear warning (GPIO19)', default=False)



def read_options_in_file(file_path, word):
    radar_arguments = ''
    try:
        with open(file_path, 'r') as fp:
            for line in fp:
                if word in line:
                    w_index = line.find(word)
                    radar_arguments = line[w_index + len(word):].strip()
                    break
    except FileNotFoundError:
        rlog.debug(f'Radar-app: {file_path} not found!')
        return
    except Exception as e:
        rlog.debug(f'Radar-app: Error {e} reading {file_path}')
        return
    return radar_arguments

def modify_line_in_file(file_path, word, new_text):    # search word in file and replace after word with new_text
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
        with open(file_path, 'w') as file:
            for line in lines:
                if word in line:
                    word_index = line.find(word)
                    new_line = line[:word_index + len(word)] + " " + new_text + "\n"
                    file.write(new_line)
                else:
                    file.write(line)
    except FileNotFoundError:
        rlog.debug(f'Radar-app: {START_RADAR_FILE} not found!')
        return
    except Exception as e:
        rlog.debug(f'Radar-app: Error {e} modifying {START_RADAR_FILE}')
        return


modes = { 'R': 'radar', 'T': 'timer', 'A': 'ahrs', 'D': 'status', 'G': 'gmeter','K': 'compass','V': 'vspeed',
        'S': 'stratux', 'I': 'flogs', 'C': 'cowarner', 'M': 'gps_dist', 'L': 'checklist'}

def parsemodes(options, radarform):
    for c in options:
        att = modes.get(c)
        if att is not None:
            radarform.getattr(radarform, att).data = True


def read_arguments(rf):
    options = read_options_in_file(START_RADAR_FILE, RADAR_COMMAND)
    if options is None:
        rlog.debug(f'Error reading options from "{START_RADAR_FILE}"')
        return
    rlog.debug(f'radar_arguments read from "{START_RADAR_FILE}": {options}')
    ap = argparse.ArgumentParser(description='Stratux options')
    arguments.add(ap)
    args = vars(ap.parse_args(options.split()))
    rf.stratux_ip.data = args['connect']
    rf.display.data = args['device']

    # radar options
    rf.ground_mode.data = args['north']
    rf.full_circle.data = args['fullcircle']
    rf.registration.data = args['registration']

    # sound options
    rf.bluetooth.data = args['bluetooth']
    rf.sound_volume.data = args['extsound']
    if rf.sound_volume.data < 0 or rf.sound_volume.data > 100:
        rf.sound_volume.data = 50
    rf.external_sound.data = args['extsound'] > 0
    rf.mixer.data = args['mixer']
    rf.speakdistance.data = args['speakdistance']
    # ground-options
    rf.groundsensor.data = args['grounddistance']
    rf.groundbeep.data = args['groundbeep']
    rf.gearindicate.data = args['gearindicate']
    # special options
    rf.no_cowarner.data = args['nocowarner']
    rf.coindicate.data = args['coindicate']
    rf.no_flighttime.data = args['noflighttime']
    rf.checklist_filename.data = args['checklist']

    parsemodes(args['displaymodes'], rf)



def write_arguments(rf):
    new_options = build_option_string(radar_form)
    modify_line_in_file(START_RADAR_FILE, RADAR_COMMAND, new_options)
    # find line with command "radar.py"
    # create arguments with content auf radar.py
    # save new line


def build_option_string(radar_form):
    out = f'-d {radar_form.display.data} -c {radar_form.stratux_ip.data}'
    rlog.debug(f'option string: {out}')
    return out

@app.route('/')
@app.route('/', methods=['GET', 'POST'])
def index():
    global wait
    watchdog.refresh()
    radar_form = RadarForm()
    read_arguments(radar_form)
    rlog.debug(f'Stratux-IP: {radar_form.stratux_ip.data}')
    if radar_form.validate_on_submit():
        rlog.debug(f'Stratux-IP after validation: {radar_form.stratux_ip.data}')
        rlog.debug(f'Mixer: {radar_form.mixer.data}')
        # write_arguments(radar_form)
        wait = MAX_WAIT_TIME
        return redirect(url_for('waiting'))
    return render_template(
        'index.html',
        radar_form=radar_form
    )


@app.route('/result', methods=['GET', 'POST'])
def result():
    watchdog.refresh()
    flash('Test')
    flash(Markup('A simple success alert with <a href="#" class="alert-link">an example link</a>. Give it a click if you like.'), 'success')
    return render_template('result.html')


@app.route('/waiting', methods=['GET', 'POST'])
def waiting():
    global status
    global wait
    watchdog.refresh()
    status += '.'
    wait -= TIMEOUT
    time.sleep(TIMEOUT)
    if wait <= 0:
        return redirect(url_for('result'))
    return render_template('waiting.html', status_indication=status)


if __name__ == '__main__':
    print("Stratux Radar Web Configuration Server " + RADAR_WEB_VERSION + " running ...")
    logging_init()
    ap = argparse.ArgumentParser(description='Stratux radar web configuration')
    ap.add_argument("-t", "--timer", type=int, required=False, help="Inactivity timer after which server will shut down", default=3)
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

    rlog.debug(f"radar-web: sudo systemctl start nginx")
    os.system('sudo systemctl start nginx')  # just in case it has been stopped before
    rlog.debug(f"radar-web: starting flask app")
    app.run(debug=flask_debug)
