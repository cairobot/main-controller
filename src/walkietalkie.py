#!/usr/bin/env python

##
# @file         walkietalkie.py
# @author       Manuel Federanko
# @version      0.0.0-r0
# @since        16-11-29
#
# @brief        This file contains the core functionality of CAiRO.
#               It is used for loading the walk-files and executing it.
#
# This is done using a multi-class aproach, every class has one task and relies on smaller
# classes previously defined. The FileWalker is the God-Class in this case.
# It loads the Program (which consists of a list of steps) and executes them.
##
                
#
# IMPORTS
#
from array import *
from math import *
import os
import abc
import math
import time
import re
import uart
import logger

#
# PRIVATE VARIABLES and FUNCTIONS
#



# input validation regex, might not be fast or beautiful, but is easy to implement and works

##
# Regex for validating input lines from the walk-files.
# _SR_ASSIGN:   specifies regex for checking variable assignmnets (ex: a=10)
# _SR_SSTEPPAT: the pattern for the specification of a single servo position in a step
# _SR_MSTEPPAT: the pattern for the specification of multiple (equal) servo positions in a step
# _SR_DELAY:    the pattern for a delay (ex 100)
# _SR_STEPPAT:  the complete pattern of a step, containing multi- and singlesteps
_SR_ASSIGN = '^[a-zA-Z][a-zA-Z0-9]*=[^\n]+$'
_SR_SSTEPPAT = '(d|r)?[0-9]+'
_SR_MSTEPPAT = _SR_SSTEPPAT + '(\.\.[0-9]+)'
_SR_DELAY = '[0-9]+'
_SR_STEPPAT = '^>('+ _SR_MSTEPPAT + '?,)+(:' + _SR_DELAY + ')?$'

##
# The compiled regex from `_SR_.*`.
_R_ASSIGN = re.compile(_SR_ASSIGN)
_R_SSTEPPAT = re.compile('^' + _SR_SSTEPPAT + '$')
_R_MSTEPPAT = re.compile('^' + _SR_MSTEPPAT + '$')
_R_DELAY = re.compile('^' + _SR_DELAY + '$')
_R_STEPPAT = re.compile(_SR_STEPPAT)


##
# Returns the current system time in ms resolution as int.
# @returns the time in ms
def _getTime():
        return int(time.time() * 1000)

##
# Splits a line at the first occuring '=' (equal) sign into two values and returns first the key and then the value.
# @param line   the line to split
# @returns      they key,value pair
def _ext_key_val(line):
        if _R_ASSIGN.match(line) == None:
                yield None
                yield None
        else:
                kv = line.split('=', 1)
                k = kv[0]
                v = kv[1]
                yield k
                yield v

##
# Loads a function from two related lines and returns true on success.
# Both lines represent a key,value pair, with one specifying an `Interval` and the other specifying a `Function`.
# @param fc     the function to load the values into
# @param l0     line 1 of the pair
# @param l1     line 2 of the pair
# @returns      a boolean denoting success
def _load_fc(fc, l0, l1):
        for line in [l0, l1]:
                k, v = _ext_key_val(line)

                if k == None and v == None:
                        return False

                if k == 'Interval':
                        ints = re.findall(r'[0-9]+', line)
                        fc.setInt(ints[0], ints[1])
                elif k == 'Function':
                        fc.setFc(v)
        return True

##
# Loads a step from the specified line and applies, if necessary a default step delay to it.
# First the line is checked for validity using a regex, only then the function continues loading the step.
# After that it fills the step array items one after another with the appropriate values.
# If an error occures the function returns Flase, otherwise True.
# @param stp            the step to load into
# @param line           the line from which to load the step
# @param default_tick   the default tick which should be applied in case no override is specified by the
#                       step definition
# @returns              True if loading was successful, otherwise False
def _load_step(stp, line, default_tick):
        if _R_STEPPAT.match(line) == None:
                stp.setSteps(array('i', (0,)*12))
                return False
        else:
                step_parts = line[1:].split(':')
                if len(step_parts) == 2:
                        stp.setDelayMs(int(step_parts[1]))
                else:
                        stp.setDelayMs(default_tick)
                i = 0
                for stp_info in step_parts[0].split(','):
                        if i == len(stp.pos):
                                break
                        if _R_SSTEPPAT.match(stp_info):
                                if stp_info[0] == 'd':
                                        stp.setServoAtDeg(i, stp_info[1:])
                                elif stp_info[0] == 'r':
                                        stp.setServoAtRad(i, float(stp_info[1:])/1000.0)
                                else:
                                        stp.setServoAtRaw(i, stp_info)
                                i += 1
                        elif _R_MSTEPPAT.match(stp_info):
                                a = stp_info.split('..')
                                for x in range(0, int(a[1])):
                                        if i ==len(stp.pos):
                                                break
                                        if a[0][0] == 'd':
                                                stp.setServoAtDeg(i, a[0][1:])
                                        elif a[0][0] == 'r':
                                                stp.setServoAtRad(i, float(a[0][1:])/1000.0)
                                        else:
                                                stp.setServoAtRaw(i, a[0])
                                        i += 1
                        else:
                                stp.setSteps(array('i', (0,)*12))
                                return False
                return True

#
# CLASSES
#

##
# The Step class is used to provide an abstraction layer to the servo positions used in the program.
# A Step consists of all 12 Servo positions and a delay. The delay specifies the time the program
# should wait before doing the next Step.
class Step:

        ##
        # Sets all 12 servo positions to zero (0) and the delay to zero (0).
        def __init__(self):
                self.pos = array('i', (0,)*12)
                self.delay = 0

        def __repr__(self):
                rep = 'Step()[pos=['
                for i in range(0, 12):
                        rep += str(int(((self.pos[i]-36.0)*191.0)/(157.0-36.0)))
                        rep += ', '
                rep += '], delay='
                rep += str(self.delay)
                rep += ']'
                return rep

        ##
        # Sets the delay of this Step in ms resolution.
        # @param dl     the delay in milliseconds
        def setDelayMs(self, dl):
                self.delay = dl

        ##
        # Sets the delay of this Step in s resolution.
        # @param dl     the delay in seconds
        def setDelay(self, dl):
                self.delay = 1000*dl

        ##
        # Adds dl milliseconds to the already existing delay.
        # @param dl     the delay to add in milliseconds
        def addDelayMs(self, dl):
                self.delay += dl

        ##
        # Adds dl seconds to the delay of this Step.
        # @param dl     the delay to add in seconds
        def addDelay(self, dl):
                self.delay += 1000*dl

        ##
        # Sets the position of servo p to v, where v is the value the pwm of the
        # microcontroller. Thus the bounds depend on the servo used and the pwm
        # configuration of the &mu;Controller.
        # @param p      the position of the servo (alias servo-#)
        # @param v      the raw value of the pwm for the servo
        def setServoAtRaw(self, p, v):
                v = int(v)
                if v > 157 or v < 35:
                        logger.DefaultLogger.warn('motor value out of range')
                self.pos[p] = v

        ##
        # Sets the position of the servo p to v, where v is given in radians.
        # @param p      the servo-#
        # @param v      the value of the servo in rad
        def setServoAtRad(self, p, v):
                v = float(v)
                self.setServoAtRaw(p, 36.0+(157.0-36.0)*v/(math.pi*191.0/180.0))

        ##
        # Sets the position of the servo p to v, where v is given in degrees.
        # @param p      the servo-#
        # @param v      the value of the servo in deg
        def setServoAtDeg(self, p, v):
                v = int(v)
                self.setServoAtRaw(p, 36.0+(157.0-36.0)*v/(191.0))

        ##
        # Provides an alias for setServoAtRaw(self, p, v).
        # Please refer to the documentation of this method.
        def setServoAt(self, p, v):
                self.setServoAtRaw(p, v);

        ##
        # Uses an array of positions to fill the Step array.
        # Filling begins with object 0 of the array and ends with
        # object `max(len(self.pos), len(stps)) - 1`.
        # @param stps   the positions to load
        def setStepsRaw(self, stps):
                for i in range(0, len(self.pos)):
                        if i == len(stps):
                                break
                        self.setServoAtRaw(i, stps[i])

        ##
        # Uses an array of positions to fill the Step array.
        # The positions are given in radians. The rest of the behaviour
        # is the same as in setStepsRaw(self, stps).
        # @param stps   the positions to load in rad
        def setStepsRad(self, stps):
                for i in range(0, len(self.pos)):
                        if i == len(stps):
                                break
                        self.setServoAtRad(i, stps[i])

        ##
        # Uses an array of positions to fill the Step array.
        # The positions are given in degrees. The rest of the behaviour
        # is the same as in setStepsRaw(self, stps).
        # @param stps   the positions to load in deg
        def setStepsDeg(self, stps):
                for i in range(0, len(self.pos)):
                        if i == len(stps):
                                break
                        self.setServoAtDeg(i, stps[i])

        ##
        # Provides an alias for setStepsRaw(self, stps).
        # Please refer to the documentation of this method.
        def setSteps(self, stps):
                self.setStepsRaw(stps)

        ##
        # Returns the raw value of the selected servo.
        # @param at     the servo-#
        # @returns      the pwm-value of the servo
        def getRawVal(self, at):
                return self.pos[at]

        ##
        # Provides an alias for getRawVal(), please refer to this method.
        def getVal(self, at):
                return self.getRawVal(at)

##
# Defines a function with a domain.
# The function is python code, which is then evaluated using the builtin eval function.
# The variable function is t, which should be mentioned by every instance.
class Function:

        ##
        # Create a new function with initialized empty string representation and a domain of [0,0].
        def __init__(self):
                self.fc_string = ''
                self.int_min = 0
                self.int_max = 0

        def __repr__(self):
                return 'Function()[fc_string=' + self.fc_string + ', int_min=' + str(self.int_min) + ', int_max=' + str(self.int_max) + ']'

        ##
        # Sets the function used to evaluate the result to fc_str.
        # @param fc_str the function used to calculate results
        def setFc(self, fc_str):
                self.fc_string = fc_str

        ##
        # Sets the domain of the function. If min is bigger than max, then
        # the values are swapped and applied.
        # @param min    the minimum value of t
        # @param max    the maximum value of t
        def setInt(self, min, max):
                mi = int(min)
                ma = int(max)
                if mi < ma:
                        self.setInt(ma, mi)
                else:
                        self.int_min = mi
                        self.int_max = ma

        ##
        # Calculates the value of the function at t=time.
        # There are only some methods made available for eval, namely everything in the math module.
        # @param time   the position at which to calculate the results.
        # @returns      the result `fc(time)`
        def getNextPos(self, time):
                var = {'__builtins__': None, 't': time }
                safe_list = ['math', 'factorial', 'acos', 'asin', 'atan', 'atan2', 'ceil', 'cos', 'cosh', 'degrees', 'e', 'exp', 'fabs', 'floor', 'fmod', 'hypot', 'log', 'log10', 'modf', 'pi', 'pow', 'radians', 'sin', 'sinh', 'sqrt', 'tan', 'tanh']
                safe_dict = dict([(key, globals().get(key, None)) for key in safe_list])
                res = eval(self.fc_string, var, safe_dict)
                return res

##
# MotorFunctions is basically just a list of Functions, which get used to calculate the value.
# Here the domain of a function is put to use. When calulating the result of the Function the
# timedifference is used. The object remembers the last_time and calculates the variable t using
# the current time minus the last time (`time=_getTime() - self.last_time`). If the time is outside
# of the domain of a function, then the next one is used, until a function is found or every one
# has been tryed (in this case None is returned). Otherwise the currect value is returned.
# The last time must be reset (or looping enabled) from a program using this class, since it on itself has no means
# of determining when to reset the last_time value.
class MotorFunctions:

        ##
        # Initializes the MotorFuntions with an empty array of functions and a last_time of zero (0).
        def __init__(self):
                self.fcs = []
                self.last_time = 0

        def __repr__(self):
                return 'MotorFunctions()[' + 'self.fcs=' + str(self.fcs) + ']'

        ##
        # Append a function to the list of Functions.
        # @param fc     the Function to append
        def append(self, fc):
                self.fcs.append(fc)

        ##
        # Returns the next value of the Function combinition. This is achieved by first determining the
        # the correct Function to use for calculations based on the domain and then returning its value.
        # Looping is essentially the "reset" of the last_time to _getTime() and then calling this method
        # again, thus ensuring that always a value unequal None will be returned.
        # @param loop   if the function should loop
        # @returns      the next position, or None
        def getNextPos(self, loop):
                time = _getTime() - self.last_time
                for i in range(0, len(self.fcs)):
                        if time >= self.fcs[i].int_min and time <= self.fcs[i].int_max:
                                ret = self.fcs[i].getNextPos(time)
                                return ret
                if loop:
                        self.last_time = _getTime() - self.fcs[0].int_min
                        return self.getNextPos(loop)
                return None

##
# An object describing a walk-file in a easy to use form for the Walker.
# It is important to note, that a Program can feature both mot- and prg-mode.
# The use of which mode can be defined by setting the Use variable in the
# walk-file to either 'mod' or 'prg'. This variable must be defined.
#
# @todo make the loader autodetect the Use.
class Program:

        ##
        # Defines the file-type header start.
        FINFO_START = '@/'
        ##
        # Defines the file-type header end.
        FINFO_STOP = '/@'

        ##
        # A tag in the file definition, for regions of loading.
        TAG_NONE = ''
        ##
        # Start the info region.
        TAG_INFO = '[info]'
        ##
        # Start the setup region.
        TAG_SETUP = '[setup]'
        ##
        # Start the prg region.
        TAG_PROG = '[prg]'
        ##
        # End a region.
        TAG_END = '[end]'

        _LOADING_NONE = 0
        _LOADING_FINFO = 1
        _LOADING_INFO = 2
        _LOADING_SETUP = 3
        _LOADING_PROG = 4
        _LOADING_M = 5

        _SR_TAGM = '^\[m[0-9]+\]$'
        _R_TAGM = re.compile(_SR_TAGM)

        ##
        # Initializes all variables to null, empty strings/lists, zero (0) or booleans to False.
        # @param fpath  the path to the file to load
        def __init__(self, fpath):
                self.fil_path = fpath
                self.file_version = ''
                self.id = 0
                self.prg_version = ''
                self.name = ''
                self.speed = 0
                self.looping = False
                self.tick = 0
                self.use = 'None'
                self.init_steps = []
                self.prg_steps = []
                self.mot_fcs = []

                for _ in range(0,12):
                        self.mot_fcs.append(MotorFunctions())

        def __repr__(self):
                return 'Program()[' + 'fil_path=' + self.fil_path + ', file_version=' + self.file_version + ', id=' + str(self.id) + ', prg_version=' + self.prg_version + ', name=' + self.name + ', speed=' + str(self.speed) + ', looping=' + str(self.looping) + ', tick=' + str(self.tick) + ', init_steps=' + str(self.init_steps) + ', prg_steps=' + str(self.prg_steps) + ', mot_fcs=' + str(self.mot_fcs) + ']'

        ##
        # Loads the program from the file.
        # This function is very forgiving and doesn't check any large-scale input.
        # If one were to define a second 'prg' section, then those instructions would just be
        # appended to the already loaded list of steps. Generally this is no problem, but
        # bear in mind, that the last definition of a section generally is the one that counts.
        def load(self):
                loading = 0
                mot_nr = -1
                unlock = False
                line0 = None
                with open(self.fil_path, 'r') as f:
                        for line in f:
                                line = line.split('#', 1)[0].strip()
                                if not line or line.isspace():
                                        continue


                                if loading == Program._LOADING_NONE:
                                        # print line
                                        if line == Program.FINFO_START:
                                                loading = Program._LOADING_FINFO
                                        elif line == Program.TAG_INFO:
                                                loading = Program._LOADING_INFO
                                        elif line == Program.TAG_SETUP:
                                                loading = Program._LOADING_SETUP
                                        elif line == Program.TAG_PROG:
                                                loading = Program._LOADING_PROG
                                        elif Program._R_TAGM.match(line) != None:
                                                mot_nr = re.findall(r'[0-9]+', line)[0]
                                                loading = Program._LOADING_M
                                        else:
                                                continue
                                else:
                                        if loading == Program._LOADING_FINFO and line == Program.FINFO_STOP or line == Program.TAG_END:
                                                loading = Program._LOADING_NONE
                                                mot_nr = -1
                                                continue
                                        
                                        # load the basic file info
                                        if loading == Program._LOADING_FINFO:
                                                k, v = _ext_key_val(line)
                                                if k == None or v == None:
                                                        continue
                                                if k == 'version':
                                                        self.file_version = v
                                        elif loading == Program._LOADING_INFO:
                                                k, v = _ext_key_val(line)
                                                if k == None or v == None:
                                                        continue

                                                if k == 'Id':
                                                        self.id = int(v)
                                                elif k == 'Version':
                                                        self.prg_version = v
                                                elif k == 'Name':
                                                        self.name = v
                                                elif k == 'Speed':
                                                        self.speed = int(v)
                                                elif k == 'Looping':
                                                        self.looping = v in ['True', 'true', 'Yes', 'yes', '1']
                                                elif k == 'Tick':
                                                        self.tick = int(v)
                                                elif k == 'Use':
                                                        self.use = v
                                        elif loading == Program._LOADING_SETUP:
                                                stp = Step()
                                                if _load_step(stp, line, self.tick):
                                                        self.init_steps.append(stp)
                                        elif loading == Program._LOADING_PROG:
                                                stp = Step()
                                                if _load_step(stp, line, self.tick):
                                                        self.prg_steps.append(stp)
                                        elif loading == Program._LOADING_M:
                                                
                                                # print line
                                                if not unlock and line == '-':
                                                        unlock = True
                                                        continue
                                                elif not unlock:
                                                        continue

                                                if line0 == None:
                                                        line0 = line
                                                else:
                                                        fc = Function()
                                                        if _load_fc(fc, line0, line):
                                                                self.mot_fcs[int(mot_nr)].append(fc)
                                                        unlock = False
                                                        line0 = None
                                                        line1 = None

                                        else:
                                                print('error')

        ##
        # Performs a crude validation of the program, checking if it is possible to execute it.
        # @returns      a boolean denoting if the program can be executed
        def validate(self):
                if self.use == 'None':
                        return False
                elif self.use == 'mot':         # use the motor functions
                        # os.write(2, 'warning: mot is deprecated\n')
                        logger.DefaultLogger.warn('mot is deprecated!')
                        if len(self.mot_fcs) != 12:
                                return False
                        for fc in self.mot_fcs:
                                if len(fc.fcs) == 0:
                                        return False
                elif self.use == 'prg':
                        return True
                else:
                        return False
                return True

##
# Provides an ABC for executing some steps.
class Walker:
        __metaclass__ = abc.ABCMeta

        def __init__(self):
                self.time = _getTime()
                self.target_diff = 0

        ##
        # Returns the next Step to execute.
        # @returns      the next Step
        @abc.abstractmethod
        def getNextStep(self):
                pass

        ##
        # Sets the next time difference, this value is used as the delay until the
        # next Step is to be executed.
        # @param diff   the time difference to set
        @abc.abstractmethod
        def setNextDiff(self, diff):
                pass

        ##
        # Executes the specified Step.
        # @param stp    the Step to execute
        @abc.abstractmethod
        def doStep(self, stp):
                pass

        ##
        # Runs one iteration of the Walker and calls the doStep function if the delay
        # has run out.
        @abc.abstractmethod
        def doTick(self):
                pass

##
# The MotorDistributor is used to automate the sending of positions to the servos.
# Since one packet consists of two (2) bytes and contains some addresses and other information,
# the MD also has a buffer of two (2) bytes.
class MotorDistributor:

        ##
        # Creates the MotorDistributer with an empty byte array of length two (2) and a uart connection.
        # @param uart   the connection to send the data to
        def __init__(self, uart):
                self.uart = uart
                self.bts = bytearray(2)

        def __repr__(self):
                return '[' + hex(self.bts[0]) + ', ' + hex(self.bts[1]) + ']'

        ##
        # Resets the buffer, since the zeroth byte's 7th bit is set to 1, the reset value
        # of byte zero is 80H.
        def reset(self):
                self.bts[0] = 0x80
                self.bts[1] = 0

        ##
        # Sets the PiC address, if the address is out of domain, False is returned, otherwise True. 
        # @param addr   the address of the PiC
        # @returns      True on success
        def setPicAddr(self, addr):
                addr = int(addr)
                if addr < 0 or addr > 3:
                        return False
                self.bts[0] |= addr << 5
                return True

        ##
        # Sets the servo address, if the address is out of domain, False is returned, otherwise True. 
        # @param addr   the address of the servo
        # @returns      True on success
        def setServoAddr(self, addr):
                addr = int(addr)
                if addr < 0 or addr > 3:
                        return False
                self.bts[0] |= (addr << 3)
                return True

        ##
        # Sets the mode of the transmission. The default mode is zero (0) and should be used when setting
        # the pwm-values of the servos. If the mode is out of domain, False is returned, otherwise True.
        # @param mode   the mode to use
        # @returns      True on success
        def setMode(self, mode):
                mode = int(mode)
                if mode < 0 or mode > 3:
                        return False
                self.bts[0] |= mode << 1
                return True

        ##
        # Sets the value of the servo. If the mode is out of domain, False is returned, otherwise True.
        # @param val    the value of the servo
        # @returns      True on success
        def setServoVal(self, val):
                val = int(val)
                if val < 0 or val > 0xff:
                        return False
                self.bts[0] |= (val >> 7) & 0x01
                self.bts[1] |= val & 0x7f;
                return True

        ##
        # Returns the bytes for inspection.
        # @returns      the data bytes
        def getData(self):
                return self.bts

        ##
        # Sends the data over the serial connection.
        # Since the PiC can't receive data that fast, a delay of
        # 50&mu;s is required to prevent data loss.
        def send(self):
                self.uart.putc(self.bts[0])
                time.sleep(50*10.0**(-6))
                self.uart.putc(self.bts[1])
                time.sleep(50*10.0**(-6))
                # time.sleep(0.1)
                # _ = self.uart.read()

##
# The FileWalker is the core handling object for loading and running walk-files.
# It keeps a list of programs in memory for fast response and loads those with a simple
# method call. The Walker can be stopped or a program unloaded.
class FileWalker(Walker):

        ##
        # Initializes all fields of this object to 0, None or empty list.
        # @param motd   the MotorDistributor to use for data transfere
        def __init__(self, motd, logger):
                Walker.__init__(self)
                self.logger = logger
                self.motd = motd
                self.prgs = {}
                self.select = None
                self.pos = 0
                self.inited = 0
                self.starttime = 0
                self.should_stop = False
                self.is_stop = True

        def __repr__(self):
                pass

        ##
        # Loads a program into the register of known programs.
        # If the programs validation succeeded, it is added to the register, otherwise it is ignored.
        # If the validation fails, False is returned, otherwise True.
        # @param path   the file from which to load
        # @returns      wheter loading was successful
        def loadProgram(self, path):
                prg = Program(path)
                prg.load()
                if prg.validate():
                        self.prgs[prg.name] = prg
                        return True
                return False

        ##
        # Selects a program from the register to use by name.
        # If a program is already selected, the method fails and returns
        # False. Otherwise it trys to load the specified program and resets
        # some initial values. If the program doesn't exist, this method
        # fails and False is returned. Otherwise True is returned.
        # @param name   the name of the program to load
        # @returns      wheter selection was successful or not
        def selectProgram(self, name):
                if self.select != None and name == None:
                        self.should_stop = True
                        return True
                if name in self.prgs:
                        self.should_stop = False
                        self.pos = 0
                        self.inited = 0
                        self.starttime = _getTime()
                        self.select = self.prgs[name]
                        return True
                return False

        ##
        # Returns the next Step to execute.
        # If 'Use' is set to 'prg', then the normal program cycle is used for generating, otherwise
        # the motor functions. Since every Program has an init instruction, this will first be
        # executed and then the normal program. If the 'Looping' is set to true, then, after completing
        # a cycle, the next first instruction from the selected section is returned again.
        # If any requirement is not met None is returned.
        # Requirements include:
        # - a program must be selected
        # - the timedifference must be higher or equal to the one specified by the previous Step
        # - if last instruction is reached: looping must be enabled
        # @returns      the next Step
        def getNextStep(self):
                if self.select == None:
                        return None

                if self.select.use == 'mot':
                        if self.inited == 0:
                                lis = self.select.init_steps
                                if self.pos >= len(lis):
                                        return
                                nstp = lis[self.pos]
                                self.pos += 1
                                if self.pos == len(lis) and self.inited == 0:
                                        self.inited = 1
                                        self.pos = 0
                                        self.starttime = _getTime()
                                        for i in range(0, len(self.select.mot_fcs)):
                                                self.select.mot_fcs[i].last_time = self.starttime

                        stp = Step()
                        stp.setDelayMs(self.select.tick)
                        for i in range(0, len(self.select.mot_fcs)):
                                d = self.select.mot_fcs[i].getNextPos(self.select.looping and not self.should_stop)
                                if d == None:
                                        return None
                                stp.setServoAtRaw(i, d)
                        return stp

                elif self.select.use == 'prg':
                        # make sure to init
                        if self.inited == 0:
                                lis = self.select.init_steps
                        else:
                                lis = self.select.prg_steps
                        if self.pos >= len(lis):
                                return None
                        nstp = lis[self.pos]
                        self.pos += 1
                        if self.pos == len(lis):
                                if self.inited == 0:
                                        self.inited = 1
                                        self.pos = 0
                                elif self.select.looping and not self.should_stop:
                                        self.pos = 0
                                else:
                                        return None
                        return nstp

        ##
        # Sends all the data for a complete Step to the hardware.
        # @param stp    the Step to send
        def doStep(self, stp):
                self.logger.debug(str(stp))
                if self.motd == None:
                        return

                # print('---')
                for i in range(0, 12):
                        # print str(i/4 + 1) + '/' + str(i%4)
                        self.motd.reset()
                        self.motd.setMode(0)
                        self.motd.setPicAddr(i / 4 + 1) # thru nr of pics ( 4 ) + offset ( 1 )
                        self.motd.setServoAddr(i % 4)
                        self.motd.setServoVal(stp.getRawVal(i))
                        self.motd.send()

        ##
        # Sets the next target time difference.
        # @param diff   the time difference
        def setNextDiff(self, diff):
                self.target_diff = diff

        ##
        # Executes a tick in the FileWalker. This method only does anything if:
        # - a program is selected
        # - the time difference requirement is met
        # and getNextStep() returns a valid Step
        def doTick(self):
                print(self.motd.uart.read());
                if self.select == None:
                        return

                if _getTime() - self.time < self.target_diff:
                        return

                sttime = _getTime()
                stp = self.getNextStep()
                if stp != None:
                        self.is_stop = False
                        self.doStep(stp)
                        self.setNextDiff(stp.delay)
                else:
                        self.is_stop = True
                        self.setNextDiff(self.select.tick)
                        self.selectProgram(None)

                self.logger.debug('exec_time: ' + str(_getTime() - sttime))
                self.time = _getTime()

#
# CODE
#
# ua = uart.Uart('/dev/tty.PL2303-00002014')
# print('  opening: ') + str(ua.open())
# motd = MotorDistributor(ua)
# fw = FileWalker(motd)
# print('  loading: ') + str(fw.loadProgram('./walkfiles/test.walk'))
# print('  loading: ') + str(fw.loadProgram('./walkfiles/mot-ex.walk'))
# print('selecting: ') + str(fw.selectProgram('Mot Test'))
# while 1:
#         fw.doTick()
