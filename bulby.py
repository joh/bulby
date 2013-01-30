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

class Bulby(object):
    def __init__(self, dev, baud=57600):
        self.dev = dev
        self.baud = baud
        self.ser = None

        self.ser = serial.Serial(self.dev, self.baud, timeout=5)
        self.ser.open()

    def command(self, command, *args):
        args = map(str, args)
        args = ' '.join(args)
        line = "{0} {1}\r".format(command, args)

        print line

        self.ser.write(line)
        self.ser.flushInput()

    def color(self, red, green, blue):
        self.command('color', red, green, blue)

    def tone(self, frequency):
        self.command('tone', frequency)

    def __del__(self):
        if self.ser:
            self.ser.close()



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
    parser.add_argument('-d', '--device', metavar='DEV', default='/dev/ttyACM*',
                        help='tty device where Bulby resides (default: %(default)s)')

    subparsers = parser.add_subparsers()

    parser_color = subparsers.add_parser('color', help='set color')
    parser_color.add_argument('red', type=IntRange(0, 255),
                              help='blazing red [0, 255]')
    parser_color.add_argument('green', type=IntRange(0, 255),
                              help='lush green [0, 255]')
    parser_color.add_argument('blue', type=IntRange(0, 255),
                              help='cool blue [0, 255]')
    parser_color.set_defaults(command='color')

    parser_color = subparsers.add_parser('tone', help='play tone')
    parser_color.add_argument('frequency', type=IntRange(0, 0xffff), help='tone frequency in Hz')
    parser_color.set_defaults(command='tone')

    args = parser.parse_args()

    try:
        device = glob.glob(args.device)[0]
    except IndexError:
        device = args.device

    try:
        bulby = Bulby(device)

        if args.command == 'color':
            bulby.color(args.red, args.green, args.blue)
        elif args.command == 'tone':
            bulby.tone(args.frequency)
        else:
            raise "This should never happen!"

    except Exception as e:
        print e
        exit(1)

if __name__ == '__main__':
    main()
