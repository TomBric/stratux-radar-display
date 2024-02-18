# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK
#
# BSD 3-Clause License
# Copyright (c) 2022, Thomas Breitbach
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
import radarmodes
import radarbuttons
import xmltodict
import json

rlog = None  # radar specific logger
# constants

# globals
g_checklist = None   # global checklist, is a list of (list_name, panda.DataFrame)
g_iterator = [0, 0]   # current position of checklist [checklist number, item no in this list]
g_checklist_changed = True


def init(checklist_xml):
    global rlog
    global g_iterator
    global g_checklist

    rlog = logging.getLogger('stratux-radar-log')
    g_iterator = [0, 0]  # start in checklist 0 at item 0
    try:
        with open(checklist_xml, "r") as f:
            xml_string = f.read()
    except FileNotFoundError:
        rlog.debug("Checklist - XML file '{0}' not found.".format(checklist_xml))
        return
    except Exception as e:
        rlog.debug("Checklist - Error '{0}' reading '{1}.".format(e, checklist_xml))
        return
    try:
        xml_dict = xmltodict.parse(xml_string)
    except Exception as e:
        rlog.debug("Checklist - Parsing of xml-checklist failed with error <{0}>".format(e))
        return
    try:
        g_checklist = xml_dict['ALL_CHECKLISTS']['CHECKLIST']
    except KeyError:
        rlog.debug("Checklist - KeyError understanding dict from xml")
    # rlog.debug("Checklist read: {0}".format(g_checklist))
    # g_checklist is now a list of checklists
    # [{'ITEM': [{'CHECK': 'Done',
    #            'REMARK': 'Please use preflight checklist',
    #            'TASK': 'Pre flight inspection'},
    #           {'CHECK': 'Locked', 'TASK': 'Seat Adjustment'}],
    #  'TITLE': 'Before Engine Start'},
    # {'ITEM': [{'CHECK': 'ON', 'TASK': 'Strobes'},
    #          {'CHECK': 'ON (SOUND)', 'TASK': 'Electr. Fuel Pump'},
    #           {'CHECK1': 'IDLE',
    #            'CHECK2': '1cm forward',
    #            'TASK': 'Power Setting',
    #           'TASK1': 'Cold Engine',
    #            'TASK2': 'Warm Enging'}],
    #  'TITLE': 'Engine Start'}]


def next_item(iterator):     # switch to next item topic in checklist
    if iterator[1] < len(g_checklist[iterator[0]]['ITEM']) - 1:
        iterator[1] += 1
    else:
        iterator[1] = 0
        if iterator[0] < len(g_checklist) - 1:
            iterator[0] += 1
        else:
            iterator[0] = 0
    return iterator


def previous_item(iterator):
    if iterator[1] > 0:
        iterator[1] -= 1
    else:
        if iterator[0] > 0:
            iterator[0] -= 1
        else:
            iterator[0] = len(g_checklist) - 1
        iterator[1] = len(g_checklist[iterator[0]]['ITEM']) - 1   # set to last item in this list
    return iterator


def previous_list(iterator):
    if iterator[0] > 0:
        iterator[0] -= 1
    else:
        iterator[0] = len(g_checklist) - 1
    iterator[1] = 0  # go to beginning of list anyhow
    return iterator


def next_list(iterator):
    iterator[1] = 0
    if iterator[0] < len(g_checklist) - 1:
        iterator[0] += 1
    else:
        iterator[0] = 0
    return iterator


def draw_checklist(display_control, ui_changed):
    global g_iterator
    global g_checklist
    global g_checklist_changed

    if ui_changed or g_checklist_changed:
        g_checklist_changed = False
        display_control.clear()
        if g_checklist is not None:
            checklist_name = g_checklist[g_iterator[0]]['TITLE']
            checklist_items = g_checklist[g_iterator[0]]['ITEM']
            last_list = (g_iterator[0] == len(g_checklist) - 1)
            try:
                display_control.checklist(checklist_name, checklist_items, g_iterator[1], last_list)
            except TypeError:
                display_control.clear()
                s = f'Checklist:"{checklist_name}"\n   Item #{g_iterator[1]+1}\n\nCorrect XML!'
                display_control.text_screen("Error", "in checklist", s, "", "Mode", "")
        else:
            display_control.text_screen("Error", "reading checklist", "\n - check file \n - check XML-format",
                                        "", "Mode", "")
        display_control.display()


def user_input():
    global g_iterator
    global g_checklist_changed

    btime, button = radarbuttons.check_buttons()
    if btime == 0:
        return 0  # stay in current mode
    g_checklist_changed = True
    if g_checklist is None:    # xml reading failed
        return radarmodes.next_mode_sequence(23)  # next mode after any press
    if button == 0 and btime == 1:  # left and short, previous item
        if g_iterator[1] == 0:  # first item, goto next list
            g_iterator = previous_list(g_iterator)
        else:
            g_iterator = previous_item(g_iterator)
        return 0
    if button == 0 and btime == 2:  # left and long
        return 3  # start next mode shutdown!
    if button == 1 and btime == 1:  # middle and short
        if g_iterator[0] == len(g_checklist)-1:   # last list
            return radarmodes.next_mode_sequence(23)  # next mode
        else:
            g_iterator = next_list(g_iterator)
            return 0
    if button == 1 and btime == 2:  # middle long
        return radarmodes.next_mode_sequence(23)  # next mode
    if button == 2 and btime == 1:  # right and short, next item
        last_item = (g_iterator == [len(g_checklist) - 1, len(g_checklist[g_iterator[0]]['ITEM']) - 1])
        if not last_item:
            g_iterator = next_item(g_iterator)
        return 0
    if button == 2 and btime == 2:  # right and long, refresh
        return 24  # start next mode for display driver: refresh called
    return 0  # no mode change
