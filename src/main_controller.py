#!/usr/bin/env python



import os
import stat
import sys
import server2
import walkietalkie
import uart
import logger
import cmd_line
import threading
import time





arg_sel = 'NONE'

# options !!!
port = 11111
s_infile = '-'
s_outfile = '-'
s_errfile = '-'
s_device = None
s_walkdir = './walkfiles/'

# parse cmd line options !!!
for arg in sys.argv:

        if arg_sel == 'NONE':
                if arg == '-p':
                        arg_sel = 'PORT'
                elif arg == '-i':
                        arg_sel = 'INFILE'
                elif arg == '-o':
                        arg_sel = 'OUTFILE'
                elif arg == '-e':
                        arg_sel = 'ERRFILE'
                elif arg == '-d':
                        arg_sel = 'DEVICE'
                elif arg == '-w':
                        arg_sel = 'WALKFILES'
                elif arg == '-h':
                        print("server for loading and executing walkfiles")
                        print('args:')
                        print('  p ... port, specify the port number')
                        print('  i ... input, specify the input file')
                        print('        this file controlls the server and (fifo)')
                        print('        if - is specified, then stdin is used')
                        print('  o ... output, please refere to -i, it behaves')
                        print('        the same, with the exception, that it sets')
                        print('        the output file')
                        print('  e ... error, refere to -i')
                        print('  d ... device, specify the rs-232 device for')
                        print('        for issueing commands to the servos')
                        print('  w ... specify the directory to be searched for')
                        print('        walkfiles')
                        print('  h ... help, print this dialog')
                        sys.exit(0)
        else:
                if arg_sel == 'PORT':
                        port = int(arg)
                elif arg_sel == 'INFILE':
                        s_infile = arg
                elif arg_sel == 'OUTFILE':
                        s_outfile = arg
                elif arg_sel == 'ERRFILE':
                        s_errfile = arg
                elif arg_sel == 'DEVICE':
                        s_device = arg
                elif arg_sel == 'WALKFILES':
                        s_walkdir = arg
                arg_sel = 'NONE'




# set the files
f_infile = None
f_outfile = None
f_errfile = None

if s_infile == '-':
        print('set input file to stdin')
        f_infile = sys.stdin
else:
        if os.path.exists(s_infile):
                f_infile = open(s_infile, "r")
                print( "set input file to " + s_infile)
        else:
                print( "failed to set input file, falling back to stdin")
                f_infile = sys.stdin


if s_outfile == '-':
        print('set output file to stdout')
        f_outfile = sys.stdout
else:
        if os.path.exists(s_outfile):
                f_outfile = open(s_outfile, "w")
                print( "set output file to " + s_outfile)
        else:
                print( "failed to set output file, falling back to stdout")
                f_outfile = sys.stdout

if s_errfile == '-':
        print('set error file to stderr')
        f_errfile = sys.stderr
else:
        if os.path.exists(s_errfile):
                f_errfile = open(s_errfile, "w")
                print( "set error file to " + s_errfile)
        else:
                print( "failed to set error file, falling back to stderr")
                f_errfile = sys.stderr


log_ = logger.Logger()
log_.setLevel(0)
if f_outfile != sys.stdout:
        log_.setLogfile(f_outfile , 0)

cmd_hdlr = cmd_line.CmdHandler(name = 'mc', infile = f_infile, outfile = f_outfile, errfile = f_errfile)





# set up uart connection to motors
log_.info('Opening uart connection on: ' + str(s_device) + '...')
if s_device == None:
        log_.warn("No uart device specified")

# ua = uart.Uart(s_device)
ua = open(str(s_device), 'wb')
#if ua.open():
#        log_.info('done')
#else:
#        log_.err('fail')

# set up motor distributor
log_.info('Creating motor distributor...')
md = walkietalkie.MotorDistributor(ua)
# md = walkietalkie.MotorDistributor(f_outfile)
log_.info('done')

# set up file walker and load programs
log_.info('Creating file walker...')
fw = walkietalkie.FileWalker(md, log_)
log_.info('done')
log_.info('Loading programs from \'' + s_walkdir + '\' ...')
if not os.path.isdir(s_walkdir):
        log_.err('fail: no such directory')
else:
        for f in os.listdir(s_walkdir):
            if f.endswith(".walk"):
                log_.info('found file: ' + f)
                log_.info('trying to load...')
                if fw.loadProgram(s_walkdir + f):
                        log_.info('loaded')
                else:
                        log_.warn('failed')

ser = server2.Server(port, cmd_hdlr, log_)
ser.setFilewalker(fw)

while ser.cmd_hdlr.looping:
        ser.do()

if ser.cliIsConn():
        ser.cli.close()
ser.ss.close()
