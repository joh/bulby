#!/usr/bin/env python
import os
import colorsys
import time
import serial

ser = serial.Serial("/dev/ttyACM0", 57600, timeout=5)
ser.open()

#fd = os.open("/dev/ttyACM0", os.O_RDWR|os.O_NONBLOCK|os.O_NOCTTY)
#m = fdpexpect.fdspawn(fd) # Note integer fd is used instead of usual string.
#m.send("\r\n")
ser.write("\r")
ser.flushInput()

start_time = time.time()
count = 0
while True:
    for h in xrange(360):
        rgb = colorsys.hsv_to_rgb(h / 360., 1.0, 1.0)
        rgb = map(lambda c: c * 255, rgb)
        r, g, b = rgb
        line = "color %d %d %d\r" % (r, g, b)
        #print time.strftime("%H:%M:%S"), line
        ser.write(line)
        ser.flushInput()
        #m.send(line)
        #m.expect("> ")

        count += 1
        delta = time.time() - start_time
        if delta > 5:
            bps = count/float(delta)
            print count, "commands written in", delta, "seconds =", bps, "commands/sec"
            count = 0
            start_time = time.time()


#os.close(fd)
ser.close()
