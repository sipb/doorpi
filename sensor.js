#!/usr/bin/node
/*
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
*/

import gpio from 'rpi-gpio'
import os from 'os'
import {exec} from 'child_process'

const DATE_FORMAT = '%a %b %d %H:%M:%S %Y'
const INPUT_PIN = 24
const LOG_PATH = '/afs/sipb.mit.edu/project/door/log'
const ZWRITE = '/usr/bin/zwrite'
const SIGNATURE = 'SIPB Door'
const REMCTL = '/usr/bin/remctl'

class DoorSensor {
  constructor(input_pin, filename) {
    this.filename = filename
    this.input_pin = input_pin
    // gpio.setmode(GPIO.BOARD)
    gpio.setup(input_pin, gpio.DIR_IN, () => {});
    gpio.on('change', this.Cycle)
  }

  LastLine() {
    try {
      let logfile = open(this.filename, 'r')
      return logfile.readlines()[-1]
    } catch (e) {
      return ''
    }
  }

  FormatTimeDelta(delta, desired_parts=2) {
    let td = new Date(delta)
    let days = delta / 86400
    let hours = td.getHours()
    let minutes = td.getMinutes()
    let seconds = td.getSeconds()
    result = []
    let Append = (lst, value, singular, plural) => {
      if(value > 0 && lst.length < desired_parts)
      lst.push(value + ' ' + (value == 1 ? singular : plural))
    }
    _Append(result, days, 'day', 'days')
    _Append(result, hours, 'hour', 'hours')
    _Append(result, minutes, 'minute', 'minutes')
    _Append(result, seconds, 'second', 'seconds')

    if(result.length == 1)
    return result[0]

    result_str = result.reduce((x, y) => x + 'and ' + y)
    return result_str
  }

  ParseLine(line) {
    let parts = line.split(',')
    if(parts.length == 0)
    return null
    if(parts.length != 5)
    throw 'Invalid line encountered: '
    try {
      return (parseInt(parts[0]), parseFloat(parts[1]),
      parts[2], parts[3], parts[4])
    } catch(e) {
      throw 'Could not convert state or seconds since epoch to integers'
    }
  }

  HumanReadableState(state) {
    let state_map = {1: 'open', 0: 'closed'}
    return state_map[state]
  }

  Cycle(channel, value, forceLog=False) {
    let status = gpio.input(this.inputPin)? 0: 1
    let box = this.ParseLine(this._LastLine())
    old_status = status + 1
    if(!box)
    oldTime = new Date().now()
    else
    [old_status, oldTime] = [...box]

    //Don't need to record, status hasn't changed
    if(status == old_status && !forceLog) return

    let now = new Date()
    let then = new Date(oldTime)
    let delta = now - then
    let delta_str = this.FormatTimeDelta(delta)
    let line = [status, now.strftime('%s'),
    this.HumanReadableState(status),
    now_eastern.strftime(DATE_FORMAT),
    delta_str].join(', ')
    this.Record(line)
    this.SendZephyr(status)
    this.SendZephyr(status, clazz='sipb-door',
    instance=self.HumanReadableState(status))
  }

  InitializeFile(self, fobj) {
    fobj.write(
      `# Log file for SIPB door sensor
      # For more information, email <sipb-door@mit.edu>
      # Format: new state, seconds since epoch, human-readable new state, human readable time, time spent in previous state`
    )
  }

  Record(self, line) {
    let logfile = open(this.filename, 'a+')
    if(!fs.existsSync(this.filename))
    this.InitializeFile(logfile)
    logfile.write(line)
  }

  SendZephyr(self, state, clazz='sipb-auto', instance='door') {
    let msg = 'The door is now %s.' % (this.HumanReadableState(state))
    let zwriteArgs = [ZWRITE, '-c', clazz, '-i', instance, '-s', SIGNATURE, '-m', msg]
    exec(zwriteArgs.join(' '))
  }
}

let sensor = new DoorSensor(INPUT_PIN, LOG_PATH)
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
function looper() {
  // All of our callbacks are on a different thread, so...
  // we wait. But don't spin the CPU.
  sleep(5).then(looper)
}