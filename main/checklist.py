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
import json
import pandas   # to read excel files
import xlrd     # to understand and convert excel

rlog = None  # radar specific logger
# constants

# globals
g_checklist = None   # global checklist, is a list of (list_name, panda.DataFrame)
g_checklist_iterator = [0, 0]   # current position of checklist [checklist number, item no in this list]


def init(checklist_xls):
    global rlog
    global checklist_iterator
    global g_checklist

    rlog = logging.getLogger('stratux-radar-log')
    try:
        raw_list = pandas.read_excel(checklist_xls, None, na_filter=False)
        # generates a dict of panda_df for an Excel with several tabs
    except FileNotFoundError:
        rlog.debug("Checklist - Excel file '{0}' not found.".format(checklist_xls))
        return
    except Exception as e:
        rlog.debug("Checklist - Error '{0}' reading '{1}.".format(e, checklist_xls))
        return
    rlog.debug("Checklist - Read following checklist from '{0}': {1}".format(checklist_xls, raw_list))
    g_checklist = list(raw_list.items())
    # g_checklist is now a list consisting of checklist-name and dataframe with items
    # to obtain an item use:  l =  l[list_no][1].iloc[item_no]
    # to obtain list_name use: l = l[list_no, 0]
    checklist_iterator = [0, 0]    # start in checklist 0 at position 0
    return g_checklist


def next_item(iterator):     # switch to next item topic in checklist
    if iterator[1] < len(g_checklist[iterator[0][1]]):
        iterator[1] = iterator[1] + 1
    else:
        iterator[1] = 0
        if iterator[0] < len(g_checklist):
            iterator = iterator[0] + 1
        else:
            iterator[0] = 0
    return iterator


def previous_item(iterator):
    if iterator[1] > 0:
        iterator[1] = iterator[1] - 1
    else:
        if iterator[0] > 0:
            iterator[0] = iterator[0] - 1
        else:
            iterator[0] = len(g_checklist)
        iterator[1] = len(g_checklist[iterator[0][1]])  # set to last item in this list
    return iterator


def draw_checklist(draw, display_control, ui_changed):
    global g_checklist_iterator
    global g_checklist
    global checklist_changed

    if ui_changed or checklist_changed:
        checklist_changed = False
        display_control.clear(draw)
        currenti = g_checklist[iterator[0]][1].iloc[iterator[1]]
        topi = None
        nexti = None
        next_nexti = None
        checklist_name = g_checklist[iterator[0]][0]
        if iterator[1] >= 1:
            topi = g_checklist[iterator[0]][1].iloc[iterator[1] - 1]
        if iterator[1] + 1 < len(g_checklist[iterator[0]][1]):
            nexti = g_checklist[iterator[0]][1].iloc[iterator[1] + 1]
        if iterator[1] + 2 < len(g_checklist[iterator[0]][1]):
            next_nexti = g_checklist[iterator[0]][1].iloc[iterator[1] + 2]
        display_control.checklist(draw, checklist_name, topi, currenti, nexti, next_nexti)
        display_control.display()


def user_input():
    global checklist_iterator
    global checklist_changed

    btime, button = radarbuttons.check_buttons()
    if btime == 0:
        return 0  # stay in current mode
    checklist_changed = True
    if button == 1 and (btime == 1 or btime == 2):  # middle in any case
        return radarmodes.next_mode_sequence(23)  # next mode
    if button == 0 and btime == 2:  # left and long
        return 3  # start next mode shutdown!
    if button == 2 and btime == 1:  # right and short, next item
        checklist_iterator = next_item(checklist_iterator)
        return 23
    if button == 0 and btime == 1:  # left and short, previous item
        checklist_iterator = previous_item(checklist_iterator)
        return 23
    if button == 2 and btime == 2:  # right and long, refresh
        return 24  # start next mode for display driver: refresh called
    return 23  # no mode change