#!/usr/bin/env python
#
# Bulby: single pixel display
#
# See README for details
#
import argparse
import colorsys
import serial
import time
import glob
import re
import math
import itertools
import glib
import dbus
import dbus.service
import dbus.mainloop.glib

def constrain(val, vmin, vmax):
    return min(max(val, vmin), vmax)

def frange(start, stop=None, step=1):
    if None is stop:
        stop = start
        start = 0

    num = int(math.ceil((stop - start) / float(step)))

    return [start + i * step for i in xrange(num)]

def linspace(start, stop, num=256):
    if start == stop:
        return list(itertools.repeat(start, num))

    step = (stop - start) / float(num-1)

    return frange(start, stop + step, step)


class BulbyService(dbus.service.Object):
    bus_name = 'com.pseudoberries.Bulby'
    object_path = '/com/pseudoberries/Bulby'

    valid_commands = ('color', 'tone')

    def __init__(self, dev, baud=57600):
        self.dev = dev
        self.baud = baud
        self.ser = None

        # TODO: Check serial lock
        self.ser = serial.Serial(self.dev, self.baud, timeout=5)
        self.ser.open()

        self.mainloop = glib.MainLoop()

        # Set up D-Bus service
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.service.BusName(self.bus_name,
                                   bus=dbus.SessionBus(),
                                   replace_existing=True)

        super(BulbyService, self).__init__(bus, self.object_path)

    def command(self, command, *args):
        args = map(str, args)
        args = ' '.join(args)
        line = "{0} {1}\r".format(command, args)

        print line

        self.ser.write(line)
        self.ser.flushInput()

    def reset(self):
        self.command('color', 0, 0, 0)
        self.command('tone', 0)

    @dbus.service.method('com.pseudoberries.Bulby', in_signature='uuu')
    def color(self, red, green, blue):
        red = constrain(red, 0, 255)
        green = constrain(green, 0, 255)
        blue = constrain(blue, 0, 255)

        self.command('color', red, green, blue)

    @dbus.service.method('com.pseudoberries.Bulby', in_signature='u')
    def tone(self, frequency):
        self.command('tone', frequency)

    def main(self):
        try:
            self.mainloop.run()
        finally:
            self.reset()
            self.ser.close()


class Bulby(object):
    def __init__(self):
        bus = dbus.SessionBus()

        bus_name = BulbyService.bus_name
        object_path = BulbyService.object_path

        self.bulby_service = bus.get_object(bus_name, object_path)
        self.color = self.bulby_service.get_dbus_method('color', bus_name)
        self.tone = self.bulby_service.get_dbus_method('tone', bus_name)

    def reset(self):
        self.color(0, 0, 0)
        self.tone(0)

    def do(self, commands, count=1):
        try:
            if count < 0:
                while True:
                    self.do_commands(commands)
            else:
                for _ in xrange(count):
                    self.do_commands(commands)
        finally:
            self.reset()

    def do_commands(self, commands):
        for item in commands:
            #print item
            cmd = item[0]
            args = item[1:]
            if cmd == 'sleep':
                time.sleep(args[0])
            elif cmd == 'color':
                self.color(*args)
            elif cmd == 'tone':
                self.tone(*args)
            else:
                print "Warning: Invalid command '{}'".format(item)

    def blink(self, red, green, blue, frequency=2, count=-1):
        period = 1. / frequency
        cmds = [('color', red, green, blue),
                ('sleep', period),
                ('color', 0, 0, 0),
                ('sleep', period)]

        self.do(cmds, count)

    def fade(self, from_color, to_color, speed=1, direction='in', count=-1):
        """ Fade from from_color to to_color

        Intermediate values are linearly interpolated
        """
        assert direction in ('in', 'out', 'inout')

        steps = 256
        period = (1. / speed) / steps

        if direction == 'out':
            from_color, to_color = to_color, from_color

        r0, g0, b0 = from_color
        r1, g1, b1 = to_color

        reds = linspace(r0, r1, steps)
        greens = linspace(g0, g1, steps)
        blues = linspace(b0, b1, steps)

        if direction == 'inout':
            reds += linspace(r1, r0, steps)
            greens += linspace(g1, g0, steps)
            blues += linspace(b1, b0, steps)
            steps *= 2

        commands = []
        for i in xrange(steps):
            commands.append(('color', reds[i], greens[i], blues[i]))
            commands.append(('sleep', period))

        self.do(commands, count)


class Color(object):
    color_names = {
        'red':    (255, 0, 0),
        'green':  (0, 255, 0),
        'blue':   (0, 0, 255),
        'yellow': (255, 255, 0),
        'purple': (255, 0, 255),
        'cyan':   (0, 255, 255),
        'white':  (255, 255, 255),
        'black':  (0, 0, 0),
    }

    def __init__(self):
        pass

    def __call__(self, arg):
        return self.parse_color(arg)

    def parse_color(self, color_string):
        # hsv(h, s, v)
        # red/green/blue/...
        # #ff0000
        rgb_range = IntRange(0, 255)
        hue_range = IntRange(0, 360)
        sat_range = IntRange(0, 100)
        val_range = IntRange(0, 100)

        # r g b
        m = re.match(r'^(\d+) (\d+) (\d+)$', color_string)
        if m:
            return map(rgb_range, m.groups())

        # rgb(r, g, b)
        m = re.match(r'^rgb\s*\((\d+),\s*(\d+),\s*(\d+)\)$', color_string)
        if m:
            return map(rgb_range, m.groups())

        # #rrggbb
        m = re.match(r'^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$', color_string)
        if m:
            rgb = map(lambda h: int(h, 16), m.groups())
            return rgb

        # hsv(h, s, v)
        m = re.match(r'^hsv\s*\((\d+),\s*(\d+),\s*(\d+)\)$', color_string)
        if m:
            hsv = (hue_range(m.group(1)) / 360.,
                   sat_range(m.group(2)) / 100.,
                   val_range(m.group(3)) / 100.)
            rgb = colorsys.hsv_to_rgb(*hsv)
            rgb = map(lambda i: int(i * 255), rgb)
            return rgb

        # color names
        if color_string in self.color_names:
            return self.color_names[color_string]

        message = "unrecognized color '{}'".format(color_string)
        raise argparse.ArgumentTypeError(message)


class IntRange(object):
    def __init__(self, min, max):
        self.min = min
        self.max = max

    def __call__(self, arg):
        try:
            value = int(arg)
        except ValueError as err:
            raise argparse.ArgumentTypeError(str(err))

        if value < self.min or value > self.max:
            message = "value {} not in range [{}, {}]".format(value, self.min, self.max)
            raise argparse.ArgumentTypeError(message)

        return value


def main():
    parser = argparse.ArgumentParser(description='Bulby: single pixel display')

    subparsers = parser.add_subparsers()

    # color <red> <green> <blue>
    sp = subparsers.add_parser('color', help='set color')
    sp.add_argument('color', type=Color(),
                    help='the color e.g. red, #ff0000, rgb(255,0,0), ...')
    sp.set_defaults(command='color')

    # tone <frequency>
    sp = subparsers.add_parser('tone', help='play tone')
    sp.add_argument('frequency', type=IntRange(0, 0xffff),
                    help='tone frequency in Hz')
    sp.set_defaults(command='tone')

    # blink [-f frequency] <red> <green> <blue>
    sp = subparsers.add_parser('blink', help='blink color')
    sp.add_argument('color', type=Color(),
                    help='the color e.g. red, #ff0000, rgb(255,0,0), ...')
    sp.add_argument('-f', '--frequency', type=float, default=2.0, metavar='F',
                    help='blink frequency in Hz (default: %(default)s Hz)')
    sp.add_argument('-n', '--times', type=int, default=-1, metavar='N',
                    help='number of times to blink, N<0 blinks forever (default: %(default)s)')
    sp.set_defaults(command='blink')

    # fade [-s speed] [-d direction] [-n times] from_color to_color
    sp = subparsers.add_parser('fade', help='fade in color')
    sp.add_argument('color1', type=Color(),
                    help='the first color e.g. red, #ff0000, rgb(255,0,0), ...')
    sp.add_argument('color2', type=Color(),
                    help='the second color e.g. red, #ff0000, rgb(255,0,0), ...')
    sp.add_argument('-s', '--speed', type=float, default=1.0, metavar='S',
                    help='fade speed in 1/s (default: %(default)s)')
    sp.add_argument('-d', '--direction', type=str, metavar='D',
                    choices=('in', 'out', 'inout'), default='in',
                    help='fade direction: in, out or inout (default: %(default)s)')
    sp.add_argument('-n', '--times', type=int, default=-1, metavar='N',
                    help='number of times to fade in, N<0 fades forever (default: %(default)s)')
    sp.set_defaults(command='fade')

    # D-bus service
    sp = subparsers.add_parser('daemon', help='start D-bus service')
    sp.set_defaults(command='daemon')
    sp.add_argument('-d', '--device', metavar='DEV', default='/dev/ttyACM*',
                    help='tty device where Bulby resides (default: %(default)s)')

    args = parser.parse_args()

    try:
        if args.command == 'daemon':
            try:
                device = glob.glob(args.device)[0]
            except IndexError:
                device = args.device

            service = BulbyService(device)
            service.main()

        else:
            bulby = Bulby()

            if args.command == 'color':
                bulby.color(*args.color)
            elif args.command == 'blink':
                bulby.blink(*args.color, frequency=args.frequency, count=args.times)
            elif args.command == 'fade':
                bulby.fade(args.color1, args.color2, args.speed, args.direction, args.times)
            elif args.command == 'tone':
                bulby.tone(args.frequency)
            else:
                raise "This should never happen!"

    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
