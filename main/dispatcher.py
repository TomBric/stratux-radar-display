#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK
#
# BSD 3-Clause License
# Copyright (c) 2022-2026, Thomas Breitbach
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


# dispatcher module for radar callbacks,
# it holds callbacks in global variables to prevent circular imports

def _noop_traffic(_message):
    return None


def _noop_situation(_message):
    return None


def _noop_shutdown():
    return None


_traffic_handler = _noop_traffic
_situation_handler = _noop_situation
_shutdown_handler = _noop_shutdown


def register_traffic_handler(handler):
    global _traffic_handler
    _traffic_handler = handler if handler is not None else _noop_traffic


def register_situation_handler(handler):
    global _situation_handler
    _situation_handler = handler if handler is not None else _noop_situation


def register_shutdown_handler(handler):
    global _shutdown_handler
    _shutdown_handler = handler if handler is not None else _noop_shutdown


def clear_handlers():
    """Release registered callbacks during shutdown to break module reference chains."""
    global _traffic_handler, _situation_handler, _shutdown_handler
    _traffic_handler = _noop_traffic
    _situation_handler = _noop_situation
    _shutdown_handler = _noop_shutdown


def emit_traffic(message: str):
    _traffic_handler(message)


def emit_situation(message: str):
    _situation_handler(message)


def emit_shutdown():
    _shutdown_handler()

