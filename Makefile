BOARD_TAG    = promicro16
BOARDS_TXT   = $(HOME)/sketchbook/hardware/SF32u4_boards/boards.txt
ARDUINO_VAR_PATH = $(HOME)/sketchbook/hardware/SF32u4_boards/variants
ARDUINO_PORT = /dev/ttyACM*
ARDUINO_LIBS =
RESET_CMD = python ../reset-leo.py

include ../Arduino.mk
