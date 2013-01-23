#!/usr/bin/env python
import os
import time
import serial
import fdpexpect

#ser = serial.Serial("/dev/ttyACM0", 57600, timeout=5)
#ser.open()
fd = os.open("/dev/ttyACM0", os.O_RDWR|os.O_NONBLOCK|os.O_NOCTTY)
m = fdpexpect.fdspawn(fd) # Note integer fd is used instead of usual string.

start_time = time.time()
count = 0
while time.time() - start_time < 10:
    #os.write(fd, "t")
    #ser.write("t")
    m.send("t")
    count += 1
    print count

#ser.close()
os.close(fd)

end_time = time.time()
delta = end_time - start_time
bps = count/float(delta)

print count, "bytes written in", delta, "seconds =", bps, "bytes/sec"

