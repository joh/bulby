#!/usr/bin/env python
#
# Bulby: single pixel display
#
# See README for details
#
# TODO list:
#  - Animation framework (easing etc)
#  - Melody play support
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

#
# Misc utils
#

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

#
# Color systems
#

def guess_dtype(data):
    if any(type(x) is float for x in data):
        return float
    else:
        return int

class rgb(tuple):
    def __new__(cls, val, dtype=None):
        try:
            r, g, b = val.to_rgb()
        except (AttributeError, TypeError):
            r, g, b = val
            if not dtype:
                dtype = guess_dtype(val)

            if dtype is int:
                r = r / 255.
                g = g / 255.
                b = b / 255.

            r = constrain(r, 0, 1)
            g = constrain(g, 0, 1)
            b = constrain(b, 0, 1)

        return super(rgb, cls).__new__(cls, (r, g, b))

    def __repr__(self):
        return 'rgb({}, {}, {})'.format(*self)

    def to_rgb(self):
        return self

class hsv(tuple):
    def __new__(cls, val, dtype=None):
        try:
            r, g, b = val.to_rgb()
            h, s, v = colorsys.rgb_to_hsv(r, g, b)
        except (AttributeError, TypeError):
            h, s, v = val

            if not dtype:
                dtype = guess_dtype(val)

            if dtype is int:
                h = h / 360.
                s = s / 100.
                v = v / 100.

        h = float(constrain(h, 0, 1))
        s = float(constrain(s, 0, 1))
        v = float(constrain(v, 0, 1))

        return super(hsv, cls).__new__(cls, (h, s, v))

    def __repr__(self):
        return 'hsv({}, {}, {})'.format(*self)

    def to_rgb(self):
        return rgb(colorsys.hsv_to_rgb(*self))

color_names = {
    'red':    rgb((1.0, 0.0, 0.0)),
    'green':  rgb((0.0, 1.0, 0.0)),
    'blue':   rgb((0.0, 0.0, 1.0)),
    'yellow': rgb((1.0, 1.0, 0.0)),
    'purple': rgb((1.0, 0.0, 1.0)),
    'cyan':   rgb((0.0, 1.0, 1.0)),
    'white':  rgb((1.0, 1.0, 1.0)),
    'black':  rgb((0.0, 0.0, 0.0)),
}

class ParseError(Exception):
    pass

def parse_color(color_string, ):
    """ Parse color string

    Supported formats:
    color = colorsys , "(", value, ")"

    colorsys = "rgb" | "hsv"

    color := r, g, b
    color := r g b
    color := #rrggbb
    color := red | green | blue | yellow | ...
    """
    # Default color system is RGB
    color_type = rgb

    #
    # Color system, e.g. rgb(value)
    #
    m = re.match(r'(\w+)\s*\((.*)\)', color_string)
    if m:
        colorsystems = {'rgb': rgb, 'hsv': hsv}
        colorsys = m.group(1)
        if not colorsys in colorsystems:
            raise ParseError("Unrecognized color system", colorsys)

        color_type = colorsystems[colorsys]
        color_string = m.group(2)

    #
    # Values separated by comma or space, e.g. "r, g, b"
    #
    m = re.match(r'.*[, ]+', color_string)
    if m:
        dtype = int
        if "." in color_string:
            dtype = float

        values = re.split(r'[ ,]+', color_string)

        try:
            values = tuple(map(dtype, values))
        except ValueError as e:
            raise ParseError(*e.args)

        return color_type(values)

    #
    # #rrggbb
    #
    m = re.match(r'#([0-9a-f]{6})', color_string, re.IGNORECASE)
    if m:
        d = int(m.group(1), 16)
        r = (d >> 16) & 0xff
        g = (d >> 8) & 0xff
        b = d & 0xff
        return color_type(rgb((r, g, b)))

    #
    # Color names, e.g. "blue"
    #
    if color_string in color_names:
        return color_type(color_names[color_string])

    raise ParseError("Unrecognized color: '{}'".format(color_string))


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
        self._color = self.bulby_service.get_dbus_method('color', bus_name)
        self._tone = self.bulby_service.get_dbus_method('tone', bus_name)

    def color(self, color):
        try:
            r, g, b = color.to_rgb()
        except (AttributeError, TypeError):
            r, g, b = color

        self._color(r * 255, g * 255, b * 255)

    def tone(self, frequency):
        self._tone(frequency)

    def reset(self):
        self.color((0, 0, 0))
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

    def blink(self, from_color, to_color=None, frequency=2, count=-1):
        """ Blink from from_color to to_color """
        if not to_color:
            ctype = type(from_color)
            to_color = ctype(rgb((0, 0, 0)))

        period = 1. / frequency
        cmds = [('color', from_color),
                ('sleep', period),
                ('color', to_color),
                ('sleep', period)]

        self.do(cmds, count)

    def fade(self, from_color, to_color, speed=1, direction='in', count=-1):
        """ Fade from from_color to to_color

        Intermediate values are linearly interpolated
        """
        assert direction in ('in', 'out', 'inout')
        assert type(from_color) is type(to_color)

        ctype = type(from_color)
        steps = 256

        if direction == 'out':
            from_color, to_color = to_color, from_color

        values = map(lambda (c0, c1): linspace(c0, c1, steps), zip(from_color, to_color))
        values = zip(*values)

        if direction == 'inout':
            values.extend(reversed(values[:-1]))
            steps = (steps * 2) - 1

        commands = []
        period = (1. / speed) / steps
        for i in xrange(steps):
            color = ctype(values[i])
            commands.append(('color', color))
            commands.append(('sleep', period))

        self.do(commands, count)


class Color(object):
    def __init__(self):
        pass

    def __call__(self, arg):
        try:
            return parse_color(arg)
        except Exception as e:
            raise argparse.ArgumentTypeError(*e.args)


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

    # blink [-f frequency] [-n times] [from_color] to_color
    sp = subparsers.add_parser('blink', help='blink color')
    sp.add_argument('from_color', type=Color(), nargs='?', default=rgb((0, 0, 0)),
                    help='the color to blink from (default: black)')
    sp.add_argument('to_color', type=Color(),
                    help='the color to blink to e.g. red, #ff0000, rgb(255,0,0), ...')
    sp.add_argument('-f', '--frequency', type=float, default=2.0, metavar='FREQ',
                    help='blink frequency in Hz (default: %(default)s Hz)')
    sp.add_argument('-n', '--times', type=int, default=-1,
                    help='number of times to blink, N<0 blinks forever (default: %(default)s)')
    sp.set_defaults(command='blink')

    # fade [-s speed] [-d direction] [-n times] [from_color] to_color
    sp = subparsers.add_parser('fade', help='fade in color')
    sp.add_argument('from_color', type=Color(), nargs='?', default=rgb((0, 0, 0)),
                    help='the color to fade from (default: black)')
    sp.add_argument('to_color', type=Color(),
                    help='the color to fade to e.g. red, #ff0000, rgb(255,0,0), ...')
    sp.add_argument('-s', '--speed', type=float, default=1.0,
                    help='fade speed in 1/s (default: %(default)s)')
    sp.add_argument('-d', '--direction', type=str, metavar='DIR',
                    choices=('in', 'out', 'inout'), default='in',
                    help='fade direction: in, out or inout (default: %(default)s)')
    sp.add_argument('-n', '--times', type=int, default=-1,
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
                bulby.color(args.color)
            elif args.command == 'blink':
                bulby.blink(args.from_color, args.to_color, args.frequency, args.times)
            elif args.command == 'fade':
                bulby.fade(args.from_color, args.to_color, args.speed, args.direction, args.times)
            elif args.command == 'tone':
                bulby.tone(args.frequency)
            else:
                raise "This should never happen!"

    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
