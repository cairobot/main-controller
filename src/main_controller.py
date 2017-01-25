#!/usr/bin/env python



import os
import stat
import sys
import server
import walkietalkie
import uart
import logger
import cmd_line
import threading
import time



##
# The MainBrainSuperServer class pieces all parts of the program together and makes it useful.
# It listens to connections, accepts them and runs programs depending on the input (commands) provided from the other line.
class MainBrainSuperServer(server.Server):

        LVL_CHAT = logger.LoggingLevel(1, '\033[1;36m' + 'CHAT' + logger.CCODES.ENDC)
        LVL_REPL = logger.LoggingLevel(1, '\033[1;35m' + 'REPL' + logger.CCODES.ENDC)

        ##
        # Start the internal FileWalker.
        class CommandStartFilewalker(cmd_line.Command):

                def __init__(self, hndlr, server):
                        cmd_line.Command.__init__(self, hndlr)
                        self.server = server

                def helper_for_thread(self):
                        while self.server.filewalker_run:
                                self.server.filewalker.doTick()


                def do(self, argv):
                        self.server.tell('starting filewalker...')
                        if self.server.runthread == None:
                                self.server.filewalker_run = True
                                self.server.runthread = threading.Thread(target=self.helper_for_thread, args=())
                                self.server.runthread.start()
                                self.server.tell('done')
                                return
                        self.server.tell('failed: already running')

        ##
        # Stop the internal FileWalker.
        class CommandStopFilewalker(cmd_line.Command):

                def __init__(self, hndlr, server):
                        cmd_line.Command.__init__(self, hndlr)
                        self.server = server

                def do(self, argv):
                        self.server.tell('stopping filewalker...')
                        self.server.filewalker_run = False
                        self.server.runthread = None
                        self.server.tell('done')

        ##
        # Select a program to run for the FileWalker.
        class CommandSelectFilewalker(cmd_line.Command):

                def __init__(self, hndlr, server):
                        cmd_line.Command.__init__(self, hndlr)
                        self.server = server

                def do(self, argv):
                        if len(argv) == 0:
                                self.server.tell('no program specified')
                                return

                        self.server.tell('selecting program ' + argv[0] + '...')
                        if self.server.filewalker.selectProgram(argv[0]):
                                self.server.tell('done')
                                return
                        self.server.tell('failed')

        ##
        # Deselect the the loaded program.
        class CommandDeselectFilewalker(cmd_line.Command):
                
                def __init__(self, hndlr, server):
                        cmd_line.Command.__init__(self, hndlr)
                        self.server = server

                def do(self, argv):
                        self.server.tell('deselecting program...')
                        self.server.tell('waiting for program end...')
                        self.server.filewalker.should_stop = True
                        while not self.server.filewalker.is_stop:
                                time.sleep(0.1)
                        self.server.tell('done')
                        self.server.filewalker.select = None
                        self.server.tell('done')

        #
        # Begin of class definition
        #
        def __init__(self, port, logger, cmdhdlr, fw):
                server.Server.__init__(self, port, logger, cmdhdlr)
                self.extcmdhdlr = cmd_line.CmdHandler(name = 'extcmd', infile = None, outfile = None, errfile = None)
                self.filewalker = fw
                self.runthread = None
                self.filewalker_run = False

                self.extcmdhdlr.regCmd('fwstart', MainBrainSuperServer.CommandStartFilewalker(self.extcmdhdlr, self))
                self.extcmdhdlr.regCmd('fwselect', MainBrainSuperServer.CommandSelectFilewalker(self.extcmdhdlr, self))
                self.extcmdhdlr.regCmd('fwdeselect', MainBrainSuperServer.CommandDeselectFilewalker(self.extcmdhdlr, self))
                self.extcmdhdlr.regCmd('fwstop', MainBrainSuperServer.CommandStopFilewalker(self.extcmdhdlr, self))

        def doAction(self, line):
                args = cmd_line._arg_split(line)
                logger.DefaultLogger.log(MainBrainSuperServer.LVL_CHAT, line)
                self.extcmdhdlr.doCmd(args[0], args[1:])

        def tell(self, line):
                logger.DefaultLogger.log(MainBrainSuperServer.LVL_REPL, line)
                self.write_to_conn(line)


# the command stop override is used to override the default stop command in order to shut down the server properly
class CommandStopOverride(cmd_line.Command):

        def __init__(self, hndlr, mbss):
                cmd_line.Command.__init__(self, hndlr)
                self.mbss = mbss

        def do(self, argv):
                self.mbss.extcmdhdlr.doCmd('fwstop')



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
                        print 'server for loading and executing walkfiles'
                        print 'args:'
                        print '  p ... port, specify the port number'
                        print '  i ... input, specify the input file'
                        print '        this file controlls the server and (fifo)'
                        print '        if - is specified, then stdin is used'
                        print '  o ... output, please refere to -i, it behaves'
                        print '        the same, with the exception, that it sets'
                        print '        the output file'
                        print '  e ... error, refere to -i'
                        print '  d ... device, specify the rs-232 device for'
                        print '        for issueing commands to the servos'
                        print '  w ... specify the directory to be searched for'
                        print '        walkfiles'
                        print '  h ... help, print this dialog'
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
        print 'set input file to stdin'
        f_infile = sys.stdin
else:
        if os.path.exists(s_infile):
                f_infile = open(s_infile, "r")
                print "set input file to " + s_infile
        else:
                print "failed to set input file, falling back to stdin"
                f_infile = sys.stdin


if s_outfile == '-':
        print 'set output file to stdout'
        f_outfile = sys.stdout
else:
        if os.path.exists(s_outfile):
                f_outfile = open(s_outfile, "w")
                print "set output file to " + s_outfile
        else:
                print "failed to set output file, falling back to stdout"
                f_outfile = sys.stdout

if s_errfile == '-':
        print 'set error file to stderr'
        f_errfile = sys.stderr
else:
        if os.path.exists(s_errfile):
                f_errfile = open(s_errfile, "w")
                print "set error file to " + s_errfile
        else:
                print "failed to set error file, falling back to stderr"
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

ua = uart.Uart(s_device)
if ua.open():
        log_.info('done')
else:
        log_.err('fail')

# set up motor distributor
log_.info('Creating motor distributor...')
md = walkietalkie.MotorDistributor(ua)
log_.info('done')

# set up file walker and load programs
log_.info('Creating file walker...')
fw = walkietalkie.FileWalker(md)
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

ser = MainBrainSuperServer(port, log_, cmd_hdlr, fw)
ser.cmdhandler.overrideCmd('stop', CommandStopOverride(ser.cmdhandler, ser))    # override default stop command to also stop the file walker when
ser.cmdhandler.run()                                                            # prompt for user