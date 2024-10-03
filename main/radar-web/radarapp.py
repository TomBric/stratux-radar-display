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
import signal
import threading
# add parent path to syspath
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import arguments
import radarmodes
import checklist
import subprocess

from flask import Flask, render_template, request, flash, redirect, url_for
from markupsafe import Markup
from flask_wtf import FlaskForm, CSRFProtect
from wtforms.validators import DataRequired, Length, Regexp, IPAddress, NumberRange
from wtforms.fields import *
from flask_bootstrap import Bootstrap5, SwitchField

RADAR_WEB_VERSION = "0.5"
START_RADAR_FILE = "../../image/stratux_radar.sh"
RADAR_COMMAND = "radar.py"       # command line to search in start_radar.sh
RADARAPP_COMMAND = "radarapp.py"  # command line to search in start_radar.sh
REBOOT_TIMEOUT = 5    # time to wait till reboot is triggered after input
MAX_SEQUENCE = 99   # maximum value accepted as sequence of modes

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
watchdog = None  # watchdog to shut dow
checklist_xml = None   # filename of checklist. Is set before editing checklist

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
    radar_seq = IntegerField('', default=1, validators=[NumberRange(min=1, max=MAX_SEQUENCE)])
    timer = SwitchField('Timer', default=True)
    timer_seq = IntegerField('', default=2, validators=[NumberRange(min=1, max=MAX_SEQUENCE)])
    ahrs = SwitchField('Artificial horizon', default=True)
    ahrs_seq = IntegerField('', default=3, validators=[NumberRange(min=1, max=MAX_SEQUENCE)])
    gmeter = SwitchField('G-Meter', default=True)
    gmeter_seq = IntegerField('', default=4, validators=[NumberRange(min=1, max=MAX_SEQUENCE)])
    compass = SwitchField('GPS based compass', default=True)
    compass_seq = IntegerField('', default=5, validators=[NumberRange(min=1, max=MAX_SEQUENCE)])
    vspeed = SwitchField('Vertical speed', default=True)
    vspeed_seq = IntegerField('', default=6, validators=[NumberRange(min=1, max=MAX_SEQUENCE)])
    cowarner = SwitchField('CO warner', default=False)
    cowarner_seq = IntegerField('', default=7, validators=[NumberRange(min=1, max=MAX_SEQUENCE)])
    flogs = SwitchField('Flight logs', default=True)
    flogs_seq = IntegerField('', default=8, validators=[NumberRange(min=1, max=MAX_SEQUENCE)])
    gps_dist = SwitchField('GPS distance measuring', default=False)
    gps_dist_seq = IntegerField('', default=9, validators=[NumberRange(min=1, max=MAX_SEQUENCE)])
    status = SwitchField('Display status', default=True)
    status_seq = IntegerField('', default=10, validators=[NumberRange(min=1, max=MAX_SEQUENCE)])
    stratux = SwitchField('Stratux status', default=True)
    stratux_seq = IntegerField('', default=11, validators=[NumberRange(min=1, max=MAX_SEQUENCE)])
    checklist = SwitchField('Checklists', default=False)
    checklist_seq = IntegerField('', default=12, validators=[NumberRange(min=1, max=MAX_SEQUENCE)])
    checklist_filename = StringField('Checklist filename', default='checklist.xml')
    edit_checklist = SubmitField('Edit checklists')

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
                             choices=[ ('0', 'never shutdown'), ('10', 'after 10 mins inactivity'),('3', 'after 3 mins inactivity'),
                                      ('1', 'after 1 min inactivity'), ('-1', 'disable web server configuration'),], default=3)


    save_restart = SubmitField('Save and reboot radar')
    save = SubmitField('Save configuration only')
    restart = SubmitField('Reboot radar only')

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


def find_line_in_file(file_path, word):
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
    except FileNotFoundError:
        rlog.debug(f'Radar-app: {START_RADAR_FILE} not found!')
    except Exception as e:
        rlog.debug(f'Radar-app: Error {e} modifying {START_RADAR_FILE}')
    for line in lines:
        if word in line:
            return line
    return None

modes = { 'R': 'radar', 'T': 'timer', 'A': 'ahrs', 'D': 'status', 'G': 'gmeter','K': 'compass','V': 'vspeed',
        'S': 'stratux', 'I': 'flogs', 'C': 'cowarner', 'M': 'gps_dist', 'L': 'checklist'}

def parsemodes(options, radarform):
    rlog.debug(f'parsing options: {options}')
    for att in modes.values():     # set default to false
        getattr(radarform, att).data = False
        getattr(radarform, att + '_seq').data = 1   # preset if later on this is selected
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
    radar_ap = argparse.ArgumentParser(description='Stratux options', exit_on_error=False)
    arguments.add(radar_ap)
    try:
        args = vars(radar_ap.parse_args(options.split()))
    except (SystemExit, argparse.ArgumentError, argparse.ArgumentTypeError) as e:
        rlog.debug(f'Error parsing radar arguments in "{START_RADAR_FILE}": {type(e)}')
        return
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
    try:
        app_args = vars(ap.parse_args(options.split()))
    except (SystemExit, argparse.ArgumentError, argparse.ArgumentTypeError) as e:
        rlog.debug(f'Error parsing radar-app arguments in "{START_RADAR_FILE}": {type(e)}')
        return
    rf.webtimeout.data = str(app_args['timer'])
    rlog.debug(f'Read web timeout of {rf.webtimeout.data} mins')

def app_option_string(radarform):
    res = f' -t {radarform.webtimeout.data}'
    return res


def build_mode_string(radarform):
    res = ''
    modestring = ''
    for i in range(1, MAX_SEQUENCE+1):    # this is a simple enumeration, no sorting
        for (key, value) in modes.items():
            if getattr(radarform, value + '_seq').data == i and getattr(radarform, value).data is True:
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
    if rf.external_sound.data is True:
        if rf.sound_volume.data < 0 or rf.sound_volume.data > 100:
            rf.sound_volume.data = 50
        out += f' -y {rf.sound_volume.data}'
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


def do_reboot():
    rlog.debug('Rebooting now')
    subprocess.run(["sudo", "reboot"])


def restart_radar():    # shutdown after some seconds to give the option for a web response
    rlog.debug(f'Starting reboot in {REBOOT_TIMEOUT} seconds')
    reboot = threading.Timer(REBOOT_TIMEOUT, do_reboot)
    reboot.start()

result_message = "Wait"

@app.route('/')
@app.route('/', methods=['GET', 'POST'])
def index():
    global result_message
    global checklist_xml

    watchdog.refresh()
    radar_form = RadarForm()
    rlog.debug(f'index(): webtimeout is {radar_form.webtimeout.data}')
    if radar_form.validate_on_submit() is not True:   # no POST request
        read_arguments(radar_form)  # in case of errors reading arguments, default is taken
        read_app_arguments(radar_form)  # in case of errors reading arguments, default is taken
    else:
        if radar_form.save_restart.data is True:
            if write_arguments(radar_form) is False:
                flash(Markup('File error saving configuration'), 'fail')
                return redirect(url_for('negative_result'))
            flash(Markup('Configuration saved!'), 'success')
            read_arguments(radar_form)  # reread arguments to get sequence nice
            read_app_arguments(radar_form)
            restart_radar()
            result_message = "Rebooting Radar. Please wait approx. 3 minutes ..."
            return redirect(url_for('result'))
        elif radar_form.save.data is True:
            if write_arguments(radar_form) is False:
                flash(Markup('File error saving configuration'), 'fail')
                return redirect(url_for('negative_result'))
            flash(Markup('Configuration successfully saved!'), 'success')
            read_arguments(radar_form)   # reread arguments to get sequence nice
            read_app_arguments(radar_form)
            return redirect(url_for('index'))
        elif radar_form.restart.data is True:
            flash(Markup('Rebooting radar ..'), 'success')
            restart_radar()
            result_message = "Rebooting Radar. Please wait approx. 3 minutes ..."
            return redirect(url_for('result'))
        elif radar_form.edit_checklist.data is True:    # button for checklists was pressed
            checklist_xml = radar_form.checklist_filename.data
            return redirect(url_for('checklist_edit'))
    return render_template('index.html',radar_form=radar_form)


class ItemForm(FlaskForm):
    task = StringField('Task', default='To check')
    check = StringField('Check', default='Check')
    remark = StringField('Remark', default='')
    task1 = StringField('Subtask1', default='')
    check1 = StringField('Check1', default='')
    task2 = StringField('Subtask2', default='')
    check2 = StringField('Check2', default='')
    task3 = StringField('Subtask3', default='')
    check3 = StringField('Check3', default='')
    delete = SubmitField('Delete')


class ChecklistForm(FlaskForm):
    name = StringField('List name', default='Unnamed')
    delete = SubmitField('Delete list!')
    edit = SubmitField('Edit List')


class ListsForm(FlaskForm):
    add = SubmitField('Add list')
    exit = SubmitField('Exit to configuration')
    lists = FieldList(FormField(ChecklistForm))


example_list = [{'ITEM': [{'CHECK': 'Done', 'REMARK': 'Please use preflight checklist', 'TASK': 'Pre flight inspection'},
                          {'CHECK': 'Locked', 'TASK': 'Seat Adjustment'}],
                'TITLE': 'Before Engine Start'},
                {'ITEM': [{'CHECK': 'ON', 'TASK': 'Strobes'},
                          {'CHECK': 'ON (SOUND)', 'TASK': 'Electr. Fuel Pump'},
                          {'CHECK1': 'IDLE', 'CHECK2': '1cm forward', 'TASK': 'Power Setting',
                                   'TASK1': 'Cold Engine', 'TASK2': 'Warm Engine'}],
                'TITLE': 'Engine Start'}]


def init_item_form(new_item, item):
    new_item.check.data = item.get('CHECK','')
    new_item.task.data = item.get('TASK', '')
    rlog.debug(f'Found task {new_item.task.data}')
    new_item.remark.data = item.get('REMARK', '')

def init_all_lists(cl):  # initializes form from all checklist (which is a dict) with an edit/delete button
    form = ListsForm()
    for one_list in cl:
        new_list = ChecklistForm()
        new_list.name.data = one_list['TITLE']
        form.lists.append_entry(new_list)
        rlog.debug(f"Appending list: {new_list.form}")
    rlog.debug(f"Returning all_lists: {form}")
    return form


def init_checklist_form(cl):     # initializes form from checklist (which is a dict)
    form = ListsForm()
    for one_list in cl:
        new_list = ChecklistForm()
        new_list.name.data = one_list['TITLE']
        for item in one_list['ITEM']:
            new_item = ItemForm()
            init_item_form(new_item, item)
            new_list.items.append_entry(new_item)
        form.lists.append_entry(new_list)
        rlog.debug(f"Form lists: {form.lists}")
    rlog.debug(f"Returning form: {form}")
    return form



@app.route('/checklist', methods=['GET', 'POST'])
def checklist_edit():
    watchdog.refresh()
    all_lists = ListsForm()
    if all_lists.validate_on_submit() is not True:   # no POST request
        all_lists = init_all_lists(example_list)
        # rlog.debug(f'Example List {example_list}')
        rlog.debug(f'all_lists-Form: {all_lists}')
    else:
        pass
        # parse checklist form
        # save checklist form
    return render_template('checklist.html', checklist_form=all_lists)


@app.route('/onechecklist', methods=['GET', 'POST'])
def onechecklist_edit():
    watchdog.refresh()
    checklist_form = ListsForm()
    if checklist_form.validate_on_submit() is not True:   # no POST request
        # checklist.init(checklist_xml)     # read_checklist. checklist is now in checklist.g_checklist
        # init_checklist_form(checklist_form, checklist.g_checklist)
        init_checklist_form(checklist_form, example_list)
        # rlog.debug(f'Example List {example_list}')
        # rlog.debug(f'Checklist-Form {checklist_form}')
    else:
        pass
        # parse checklist form
        # save checklist form
    return render_template('checklist.html', checklist_form=checklist_form)


@app.route('/negative_result', methods=['GET', 'POST'])
def negative_result():
    watchdog.refresh()
    return render_template('negative_result.html', status_indication=status)


@app.route('/result', methods=['GET', 'POST'])
def result():
    watchdog.refresh()
    return render_template('result.html', result_message=result_message)



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

