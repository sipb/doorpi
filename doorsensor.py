# Door sensor script
# March 2013
# cdolan@mit.edu

import RPi.GPIO as GPIO
import subprocess, os, datetime, random

DATE_FORMAT = '%a %b %d %H:%M:%S %Y'

INPUT_PIN = 24

#LOGFILE = "/afs/sipb/project/door/log";
#LOGFILEBACKUP = "/tmp/doorsensor_bk";
LOGFILE = "foo.txt"

#$ENV{"KRB5CCNAME"} = "/tmp/krb5cc_door";
#$ENV{"KRBTKFILE"} = "/tmp/tkt_door";

# Use the default pin assignments
GPIO.setmode(GPIO.BOARD)

# Declare the INPUT_PIN for use as an input
GPIO.setup(INPUT_PIN, GPIO.IN)

"""
# Initialize kerberos and afs authentication
subprocess.call(["/usr/athena/bin/kinit", "-45", "-k", "-t", "/etc/krb5.keytab"])
subprocess.call(["/bin/athena/aklog", "sipb"])

def reportError(error_name, error_message):
	subprocess.call(["/usr/athena/bin/zwrite", "-c", "sipb-door", "-i", "error",  "-m", "'Error: {0}\n{1}'".format(error_name, error_message)])
	subprocess.call(["/bin/athena/unlog"])
	subprocess.call(["/usr/athena/bin/kdestroy"])
	exit(0)

"""
# Try to open the file
# if none exits, create it
f = open(LOGFILE, 'a+')

current_state = None
last_time = None
force_log = False

if os.stat(f.name).st_size == 0:
	print "file is empty"
	#the log file is empty, write the header
	f.write("# Logfile for the SIPB door sensor\n")
	f.write("# <sipb-door\@mit.edu>\n")
	f.write("# Format:\n")
	f.write("# new state, current time, human-readable new state, human-readable time, time spent in previous state\n")
	current_state = 0
	last_time = datetime.datetime.now()
	force_log = True

print "at process"
print current_state, last_time

# get the last line
output = subprocess.check_output(["tail", "-n", "1", f.name])

print "output is", output

if current_state == None:
	current_state = int(output.split(',')[0])
	
if last_time == None:
	last_time = datetime.datetime.strptime(output.split(',')[3], DATE_FORMAT)

#input_value = GPIO.input(INPUT_PIN)
input_value = random.choice([0,1])


if input_value != current_state or force_log == True:
	now = datetime.datetime.now()
 
	seconds_since_epoch = now.strftime('%s')

	human_readable_time = now.strftime(DATE_FORMAT)
	
	input_state_text = "open" if input_value == 0 else "closed"

	print "now", now
	print "last_time", last_time
	#Yuck! string formatting for last log entry
	time_delta = str(last_time - now).split(',')
	print "time_delta", time_delta
	days_since_last_open = time_delta[0] if len(time_delta) > 1 else ""
	
	if len(time_delta) > 1:
		time_delta = time_delta[1].split(':')
		print "splitting time delta"
		print "new time_delta is", time_delta
	
	hours = int(time_delta[0].strip())
	minutes = int(time_delta[1].strip())
	seconds = int(float(time_delta[2].strip()))
	
	hours_since_last_open = ""
	if hours > 0:
		hours_since_last_open = str(hours) + " hour" + ("s" if hours > 1 else "")
	
	minutes_since_last_open = ""
	if minutes > 0:
		minutes_since_last_open = str(minutes) + " minute" + ("s" if minutes > 1 else "")

	seconds_since_last_open = ""
	if seconds > 0:
		seconds_since_last_open = str(seconds)+ " second" + ("s" if seconds > 1 else "")
	
	time_since_last_open = " ".join([days_since_last_open, hours_since_last_open, minutes_since_last_open, seconds_since_last_open])

	f.write(",".join([str(input_value), seconds_since_epoch, input_state_text, human_readable_time, time_since_last_open]) + "\n")

f.close()
