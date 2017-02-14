#!/usr/bin/python2
"""
SIPB Door Sensor Daemon.

A project of the SIPB Joint Chiefs, who proudly present the DoorPi, a
hybrid Defense Condition notification, door status notification, and
general badass LED signage SIPB "office head".

This file implements a long-lived daemon that periodically checks the
state of the door, through the given GPIO pins. This assumes that the
door sensor is connected to the 3.3V output on the Pi, and a
programmable GPIO that has been configured to use pull-down, as a reed
sensor will float in one of its configurations.

This script assumes that Kerberos tickets and AFS tokens are already
present; it should be paired with k5start to guarantee their liveness.
"""

import datetime
import os
import pytz
import subprocess
import sys
import time

from RPi import GPIO

DATE_FORMAT = '%a %b %d %H:%M:%S %Y'
INPUT_PIN = 24
LOG_PATH = '/afs/sipb.mit.edu/project/door/log'
ZWRITE = '/usr/bin/zwrite'
SIGNATURE = 'SIPB Door'
REMCTL = '/usr/bin/remctl'

class ParseError(Exception):
    pass

class DoorSensor(object):
    def __init__(self, input_pin, filename):
        self._filename = filename
        self._input_pin = input_pin
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self._input_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        def Callback(channel):
            self.Cycle()
        GPIO.add_event_detect(self._input_pin, GPIO.BOTH,
                              callback=Callback, bouncetime=100)

    def _InitializeFile(self, fobj):
        fobj.write("""# Log file for SIPB door sensor
# For more information, email <sipb-door@mit.edu>
# Format: new state, seconds since epoch, human-readable new state, human readable time, time spent in previous state
""")

    def _LastLine(self):
        try:
            with open(self._filename, 'r') as logfile:
                return logfile.readlines()[-1]
        except IOError:
            return ''

    def _FormatTimeDelta(self, td, desired_parts=2):
        seconds = td.total_seconds()
        days, rem = divmod(seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, seconds = divmod(rem, 60)
        result = []
        def _Append(lst, value, singular, plural):
            if value > 0 and len(lst) < desired_parts:
                lst.append('%d %s' % (value,
                                      singular if value == 1 else plural))
        _Append(result, days, 'day', 'days')
        _Append(result, hours, 'hour', 'hours')
        _Append(result, minutes, 'minute', 'minutes')
        _Append(result, seconds, 'second', 'seconds')

        if len(result) == 1:
            return result[0]
        result_str = result[0]
        for i in xrange(1, len(result)):
            result_str += ' and %s' % (result[i])
        return result_str

    def PollSensor(self):
        return 0 if GPIO.input(self._input_pin) else 1

    def ParseLine(self, line):
        if not line:
            return None
        parts = line.split(',')
        if len(parts) != 5:
            raise ParseError('Invalid line encountered: ' + line)
        try:
            return (int(parts[0]), float(parts[1]),
                    parts[2], parts[3], parts[4])
        except:
            raise ParseError(
                'Could not convert state or seconds since epoch to integers')

    def _HumanReadableState(self, state):
        state_map = {1: 'open', 0: 'closed'}
        return state_map[state]

    def Cycle(self, force_log=False):
        status = self.PollSensor()
        box = self.ParseLine(self._LastLine())
        old_status = status + 1
        if box is None:
            old_time = float(datetime.datetime.now().strftime('%s'))
        else:
            old_status, old_time, _, _, _ = box
        if status == old_status and not force_log:
            # Don't need to record, status hasn't changed
            return
        eastern = pytz.timezone('US/Eastern')
        now = datetime.datetime.now(pytz.utc)
        now_eastern = now.astimezone(eastern)
        then = datetime.datetime.fromtimestamp(old_time, pytz.utc)
        delta = now - then
        delta_str = self._FormatTimeDelta(delta)
        line = '%d,%s,%s,%s,%s\n' % (status, now.strftime('%s'),
                                     self._HumanReadableState(status),
                                     now_eastern.strftime(DATE_FORMAT),
                                     delta_str)
        sys.stdout.write(line)
        self.Record(line)
        self.SendZephyr(status)
        self.SendZephyr(status, clazz='sipb-door',
                        instance=self._HumanReadableState(status))
        #if status == 1:
        #    self.Alert()

    def Record(self, line):
        with open(self._filename, 'a+') as logfile:
            if os.fstat(logfile.fileno()).st_size == 0:
                self._InitializeFile(logfile)
            logfile.write(line)

    def SendZephyr(self, state, clazz='sipb-auto', instance='door'):
        msg = 'The door is now %s.' % (self._HumanReadableState(state),)
        zwrite_args = [ZWRITE, '-c', clazz, '-i', instance,
                       '-s', SIGNATURE, '-m', msg]
        subprocess.call(zwrite_args)

    def Alert(self, host='zsr.mit.edu'):
        remctl_args = [REMCTL, host, 'alert']
        subprocess.call(remctl_args)

if __name__ == '__main__':
    sensor = DoorSensor(INPUT_PIN, LOG_PATH)
    while True:
        # All of our callbacks are on a different thread, so...we
        # wait. But don't spin the CPU.
        time.sleep(5)
