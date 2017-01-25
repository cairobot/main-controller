#!/usr/bin/env python

##
# @file         uart.py
# @author       Manuel Federanko
# @version      0.0.0-r0
# @since        16-11-29
#
# @brief        A Simple implementation of a UART connection with a python interface.
#               The Library running in the background is a c library.
#
# The purpose of this "library" is to be an alternative to pyserial, because I experienced trouble with it.
# It's not like it didn't straight up not work, it worked only about 2% of the time without any changes to the code.
##

#
# IMPORTS
#
import os
import ctypes
import time

#
# PRIVATE VARIABLES and FUNCTIONS
#
_DEFAULT_LIB_PATH = './lib/libuart.dylib'
_DEFAULT_LIB = ctypes.CDLL(_DEFAULT_LIB_PATH)

#
# CLASSES
#

##
# Defines a wrapper class for accessing the underlying uart library for accessing serial ports.
class Uart:

        ##
        # Initializes the connection on the device portstr with a buffer size of buffsize.
        # @param portstr        the device to connect to
        # @param buffsize       the io buffer size
        def __init__(self, portstr, buffsize=1024):
                self.id = -1
                self.buff = ctypes.create_string_buffer(buffsize)
                self.portstr = portstr

        ##
        # Opens the device for reading and writing and returns True on success.
        # @returns      a boolean denoting success
        def open(self):
                if self.portstr == None:
                        return False
                self.id = _DEFAULT_LIB.uart_open(self.portstr)
                if self.id < 0:
                        return False
                return True

        ##
        # Closes the device and returns True on success.
        # @returns      a boolean denoting success
        def close(self):
                if self.portstr == None:
                        return False
                ret = _DEFAULT_LIB.uart_close(self.id)
                self.id = -1
                if ret < 0:
                        return False
                return True

        ##
        # Writes the specified string to the connection and returns True on success.
        # @param st     the string to send
        # @returns      the status boolean
        def write_string(self, st):
                if self.portstr == None:
                        return False
                string = str(st)
                if _DEFAULT_LIB.uart_write(self.id, string, len(string)) < 0:
                        return False
                return True

        ##
        # Writes a byte array to the device connected and returns True on success.
        # @param dat_arr        the data to send
        # @returns              the status boolean
        def write_raw(self, dat_arr):
                if self.portstr == None:
                        return False
                typ = ctypes.c_char * len(dat_arr)
                h = typ.from_buffer(dat_arr)
                if _DEFAULT_LIB.uart_write(self.id, h, len(h)) < 0:
                        return False
                return True

        ##
        # Provides an alias for write_raw(), please consult the documentation of this
        # method.
        # @param dat_arr_st     the data to write
        # @returns              the status boolean
        def write(self, dat_arr_st):
                return self.write_raw(dat_arr_st)

        ##
        # Writes a char to the device, and returns True on success.
        # @param c      the character to send
        # @returns      the status boolean
        def putc(self, c):
                ba = bytearray(1)
                ba[0] = c
                return self.write_raw(ba)

        ##
        # Reads a string from the connection and returns the it or None, if no data is available.
        # @returns      the string or None
        def read_string(self):
                if self.portstr == None:
                        return None
                l = _DEFAULT_LIB.uart_read(self.id, self.buff, len(self.buff))
                if l < 0:
                        return None
                return self.buff.raw[:l]

        ##
        # Provides an alias for read_string(), please consult the docuentation of this method.
        # @returns      the string or None
        def read(self):
                return self.read_string()

#
# CODE
#

# EXAMPLE:
# ser = Uart('/dev/tty.PL2303-00002014')
# print ser.open()
# ser.putc(0xC3)
# ser.putc(125)
# time.sleep(1)
# print ser.read()
# ser.close()
