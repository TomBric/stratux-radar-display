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
import shutdownui
import psutil

from flask import Flask, render_template, request, flash, redirect, url_for
from markupsafe import Markup
from flask_wtf import FlaskForm, CSRFProtect
from wtforms.validators import DataRequired, Length, Regexp, IPAddress
from wtforms.fields import *
from flask_bootstrap import Bootstrap5, SwitchField

RADAR_WEB_VERSION = "0.5"
START_RADAR_FILE = "../../image/stratux_radar.sh"
RADAR_COMMAND = "radar.py"       # command line to search in start_radar.sh
RADARAPP_COMMAND = "radar-app.py"  # command line to search in start_radar.sh
TIMEOUT = 0.5
MAX_WAIT_TIME = 10
RADAR_PROCESS_NAME = "radar.py"   # process name to search for and restart/terminate

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

    def new_timeout(self, timeout):
        self.stop()
        self.timeout = timeout
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

    # web options
    webtimeout = RadioField('Configuration shutdown',
                             choices=[ ('-1', 'never shutdown'), ('10', 'after 10 mins inactivity'),('3', 'after 3 mins inactivity'),
                                      ('1', 'after 1 min inactivity'), ('0', 'Disable web server configuration'),], default=3)


    save_restart = SubmitField('Save and restart radar')
    save = SubmitField('Save configuration only')
    restart = SubmitField('Restart radar only')

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
                    if '&' in radar_arguments:
                        radar_arguments = radar_arguments.split('&')[0].strip()  # ignore & at the end
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
                    new_line = line[:word_index + len(word)] + " " + new_text + " &\n"
                    file.write(new_line)
                else:
                    file.write(line)
    except FileNotFoundError:
        rlog.debug(f'Radar-app: {START_RADAR_FILE} not found!')
        return False
    except Exception as e:
        rlog.debug(f'Radar-app: Error {e} modifying {START_RADAR_FILE}')
        return False
    return True

modes = { 'R': 'radar', 'T': 'timer', 'A': 'ahrs', 'D': 'status', 'G': 'gmeter','K': 'compass','V': 'vspeed',
        'S': 'stratux', 'I': 'flogs', 'C': 'cowarner', 'M': 'gps_dist', 'L': 'checklist'}

def parsemodes(options, radarform):
    rlog.debug(f'parsing options: {options}')
    for att in modes.values():     # set default to false
        getattr(radarform, att).data = False
        getattr(radarform, att + '_seq').data = 0
    sequence = 1
    for c in options:
        att = modes.get(c)
        if att is not None:
            getattr(radarform, att).data = True
            getattr(radarform, att + '_seq').data = sequence
            sequence += 1

def read_arguments(rf):
    options = read_options_in_file(START_RADAR_FILE, RADAR_COMMAND)
    if options is None:
        rlog.debug(f'Error reading options from "{START_RADAR_FILE}"')
        return
    rlog.debug(f'radar_arguments read from "{START_RADAR_FILE}": {options}')
    radar_ap = argparse.ArgumentParser(description='Stratux options')
    arguments.add(radar_ap)
    args = vars(radar_ap.parse_args(options.split()))
    rf.display.data = args['device']
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

def read_app_arguments(rf):
    options = read_options_in_file(START_RADAR_FILE, RADARAPP_COMMAND)
    if options is None:
        rlog.debug(f'Error reading options from "{START_RADAR_FILE}"')
        return
    rlog.debug(f'radarapp_arguments read from "{START_RADAR_FILE}": {options}')
    app_args = vars(ap.parse_args(options.split()))
    rf.webtimeout.data = str(app_args['timer'])
    rlog.debug(f'Read web timeout of {rf.webtimeout.data} mins')

def app_option_string(radarform):
    res = f' -t {radarform.webtimeout.data}'
    return res


def build_mode_string(radarform):
    res = ''
    modestring = ''
    for (key, value) in modes.items():
        if getattr(radarform, value).data is True:
            modestring += key
    if len(modestring) > 0:
        res = f' -modes {modestring}'
    return res

def write_arguments(rf):
    new_options_app = app_option_string(rf)
    rlog.debug(f'New option string for radar web: "{new_options_app}"')
    if modify_line_in_file(START_RADAR_FILE, RADARAPP_COMMAND, new_options_app) is False:
        return False
    new_options = build_option_string(rf)
    rlog.debug(f'New option string for radar: "{new_options}"')
    if modify_line_in_file(START_RADAR_FILE, RADAR_COMMAND, new_options) is False:
        return False
    return True

def build_option_string(rf):
    out = f'-d {rf.display.data} -c {rf.stratux_ip.data}'
    out += build_mode_string(rf)
    if rf.ground_mode.data is True:
        out += ' -n'
    if rf.full_circle.data is True:
        out += ' -e'
    if rf.registration.data is True:
        out += ' -r'
    if rf.bluetooth.data is True:
        out += ' -b'
    if rf.sound_volume.data is True:
        if rf.sound_volume.data < 0 or rf.sound_volume.data > 100:
            rf.sound_volume.data = 50
        out += ' -y rf.sound_volume.data'
        if len(rf.mixer.data) > 0:
            out += f' -mx {rf.mixer.data}'
    if rf.speakdistance.data is True:
        out += ' -sd'
    if rf.groundsensor.data is True:
        out += ' -gd'
    if rf.groundbeep.data is True:
        out += ' -gb'
    if rf.gearindicate.data is True:
        out += ' -gi'
    if rf.no_cowarner.data is True:
        out += ' -nc'
    if rf.coindicate.data is True:
        out += ' -ci'
    if rf.no_flighttime.data is True:
        out += ' -nf'
    if rf.checklist.data is True and len(rf.checklist_filename.data) > 0:
        out += f' -chl {rf.checklist_filename.data}'
    return out


def restart_radar():    # shutdown and restart radar-app
    global wait
    wait = MAX_WAIT_TIME
    radar_name = RADAR_PROCESS_NAME
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == radar_name:
            rlog.debug(f"Terminating process {proc.info['name']} with pid {proc.info['pid']}.")
            proc.terminate()  # Prozess beenden

def is_radar_running():
    radar_name = RADAR_PROCESS_NAME
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == radar_name:
            return True
    return False


waiting_message = 'Waiting'

@app.route('/')
@app.route('/', methods=['GET', 'POST'])
def index():
    global waiting_message
    watchdog.refresh()
    radar_form = RadarForm()
    if radar_form.validate_on_submit() is not True:   # no POST
        read_arguments(radar_form)
        read_app_arguments(radar_form)
    else:     # validated POST request
        if radar_form.save_restart.data is True:
            if write_arguments(radar_form) is False:
                flash(Markup('File error saving configuration'), 'fail')
                return redirect(url_for('negative_result'))
            waiting_message = 'Configuration saved. Restarting radar ..'
            restart_radar()
            if radar_form.webtimeout.data == 0:
                rlog.debug(f'Disabling radar config app due to new configuration!')
                watchdog.do_expire()
            else:
                rlog.debug(f'Setting new watchdog timeout to {radar_form.webtimeout.data} mins')
                watchdog.new_timeout(radar_form.webtimeout.data)
            return redirect(url_for('waiting'))
        elif radar_form.save.data is True:
            if write_arguments(radar_form) is False:
                flash(Markup('File error saving configuration'), 'fail')
                redirect(url_for('negative_result'))
            flash(Markup('Configuration successfully saved!'), 'success')
            return render_template('index.html',radar_form=radar_form)
        elif radar_form.restart.data is True:
            waiting_message = 'No configuration saved. Restarting radar ..'
            restart_radar()
            return redirect(url_for('waiting'))
    return render_template('index.html',radar_form=radar_form)


@app.route('/waiting', methods=['GET', 'POST'])
def waiting():
    global status
    global wait
    watchdog.refresh()
    if is_radar_running() is False:
        flash(Markup(waiting_message), 'success')
        return redirect(url_for('index'))
    status += '.'
    wait -= TIMEOUT
    time.sleep(TIMEOUT)
    if wait <= 0:
        return redirect(url_for('negative_result'), reason='Could not terminate running radar-process.')
    return render_template('waiting.html', message=waiting_message, status_indication=status)


@app.route('/negative_result', methods=['GET', 'POST'])
def negative_result():
    watchdog.refresh()
    return render_template('negative_result.html', status_indication=status)


if __name__ == '__main__':
    print("Stratux Radar Web Configuration Server " + RADAR_WEB_VERSION + " running ...")
    logging_init()
    ap = argparse.ArgumentParser(description='Stratux radar web configuration')
    ap.add_argument("-t", "--timer", type=int, required=False,
                    help="Inactivity timer after which server will shut down", default=3)
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
    if shutdown_timer > 0:  # if zero: set no timeout
        watchdog.start()
    if shutdown_timer < 0:
        rlog.debug(f"radar-web: not starting")
        watchdog.do_expire()   # do not start at all, terminate nginx and this process

    rlog.debug(f"radar-web: sudo systemctl start nginx")
    os.system('sudo systemctl start nginx')  # just in case it has been stopped before
    rlog.debug(f"radar-web: starting flask app")
    app.run(debug=flask_debug)
