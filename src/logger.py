#!/usr/bin/env python

##
# @file         logger.py
# @author       Manuel Federanko
# @version      0.0.0-r1
# @since        16-11-29
# 
# @brief        A simple and easy to use logging system, which prints date
#               and level of the logged information and optionally does log everything to a file.
##

#
# IMPORTS
#
import sys
import time

#
# PRIVATE VARIABLES and FUNCTIONS
#


#
# CLASSES
#

##
# A Class containing the default terminal color-codes
class CCODES:
        HEADER = '\033[95m'
        OKBLUE = '\033[94m'
        OKGREEN = '\033[92m'
        WARNING = '\033[93m'
        FAIL = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'

##
# Represents the logging level of the Logger, this level has an integer value and a string value for deciding if it is to display and how to display it.
class LoggingLevel:

        def __init__(self, lvl, name):
                self.lvl = lvl
                self.name = name

##
# The Logger has some default builtin methods for pretty-printing log messages.
# The messages are in the form of `[<LOGINFO>][<date>]: message`.
class Logger:

        LVL_DBUG = LoggingLevel(0, 'DBUG')
        LVL_INFO = LoggingLevel(1, CCODES.OKBLUE + 'INFO' + CCODES.ENDC)
        LVL_WARN = LoggingLevel(2, CCODES.WARNING + 'WARN' + CCODES.ENDC)
        LVL_ERRO = LoggingLevel(3, CCODES.FAIL + ' ERR' + CCODES.ENDC)
        
        def __init__(self):
                self.level = 0
                self.filelvl = 0
                self.file = None

        ##
        # Sets the level of this Logger to lvl.
        # @param lvl    the level to display, if the logging level is higher or equal to this level, then the messages in printed to the output stream given
        def setLevel(self, lvl):
                self.level = lvl

        ##
        # Sets a logfile, which records all logs which are bigger or equal to lvl.
        # @param filestr        the file object
        # @param lvl            set the logging level of the file
        def setLogfile(self, file, lvl):
                self.file = file
                self.filelvl = lvl

        ##
        # Remove the logfile.
        def unsetLogfile(self):
                if self.file != None:
                        self.file.close()
                        self.file = None

        ##
        # Print a generic log message, where ll is the loglevel as string and msg is the message to display.
        # @param ll     the level name
        # @param msg    the message to display
        def log(self, ll, msg):
                date = time.strftime('%Y-%m-%d/%H:%M:%S')
                string = '[' + ll.name + '][' + date + ']:' + msg
                if ll.lvl >= self.level:
                        sys.stdout.write(string + '\n')
                        sys.stdout.flush()
                if self.file != None and ll.lvl >= self.filelvl:
                        self.file.write(string + '\n')
                        self.file.flush()

        ##
        # Prints a debug message.
        # @param msg    the message to display
        def debug(self, msg):
                self.log(Logger.LVL_DBUG, msg)

        ##
        # Prints an info.
        # @param msg    the message to display
        def info(self, msg):
                self.log(Logger.LVL_INFO, msg)

        ##
        # Prints a warning.
        # @param msg    the message to display
        def warn(self, msg):
                self.log(Logger.LVL_WARN, msg)

        ##
        # Prints an error.
        # @param msg    the message to display
        def err(self, msg):
                self.log(Logger.LVL_ERRO, msg)

#
# CODE
#
# The default logger with lvl = Info
DefaultLogger = Logger()
DefaultLogger.setLevel(1)