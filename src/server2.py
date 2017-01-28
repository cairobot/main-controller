#!/usr/bin/env python

##
# author:   
# file:     server2.py
# version:  0.0.0-r0
# since:    
# desc:
##

###
# IMPORTS
###
import socket
import os
import sys
import fcntl
import time
import select

import cmd_line

###
# PRIVATE VARIABLES and FUNCTIONS
###


###
# CLASSES
###
class Server:

        CONNECTION_BUFFER_LEN = 1024

        class CommandFWStart(cmd_line.Command):

                def __init__(self, hdlr, server):
                        cmd_line.Command.__init__(self, hdlr)
                        self.server = server

                def do(self, argv):
                        self.server.logger.info("starting filewalker")
                        self.server.fw_run = True

        class CommandFWStop(cmd_line.Command):

                def __init__(self, hdlr, server):
                        cmd_line.Command.__init__(self, hdlr)
                        self.server = server

                def do(self, argv):
                        self.server.logger.info("stopping filewalker")
                        self.server.fw_run = False

        class CommandFWSelect(cmd_line.Command):

                def __init__(self, hdlr, server):
                        cmd_line.Command.__init__(self, hdlr)
                        self.server = server

                def do(self, argv):
                        if len(argv) == 0:
                                self.server.logger.info("deselecting program")
                                self.server.fw.should_stop = True
                                self.server.logger.info("done")
                        elif len(argv) == 1:
                                self.server.logger.info("selected program: " + argv[0])
                                self.server.fw.selectProgram(argv[0])

        class CommandStop(cmd_line.Command):

                def __init__(self, hdlr, server):
                        cmd_line.Command.__init__(self, hdlr)
                        self.server = server

                def do(self, argv):
                        self.server.logger.info("stopping server")
                        self.server.cmd_hdlr.doCmd('fwstop')



        def __init__(self, port, cmd_hdlr, logger):
                self.cmd_hdlr = cmd_hdlr
                self.logger = logger
                self.ss = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.ss.bind(('', port))
                self.ss.setblocking(False)
                self.ss.listen(1)

                self.cli = None
                self.fw = None
                self.fw_run = False

                self.cmd_hdlr.regCmd('fwstart', Server.CommandFWStart(self.cmd_hdlr, self))
                self.cmd_hdlr.regCmd('fwstop', Server.CommandFWStop(self.cmd_hdlr, self))
                self.cmd_hdlr.regCmd('fwselect', Server.CommandFWSelect(self.cmd_hdlr, self))
                self.cmd_hdlr.overrideCmd('exit', Server.CommandStop(self.cmd_hdlr, self))


        def setFilewalker(self, fw):
                self.fw = fw

        def cliIsConn(self):
                return self.cli != None

        def cliAccept(self):
                if self.cliIsConn():
                        return
                try:
                        (self.cli, _) = self.ss.accept()
                except socket.error, e:
                        if e.errno == 35:
                                return
                        else:
                                print e
                        return


        def cliRead(self):
                #if self.cli == None:
                #        return None
                #try:
                #        data = self.cli.recv(1024)
                #except socket.timeout, e:
                #        err = e.args[0]
                #        if err == 'timed out':
                #                # no data available
                #                return None
                #        else:
                #                # error
                #                print e
                #                return None
                #except socket.error, e:
                #        if e.errno == 35:
                #                return None
                #        print e
                #        return None
                #else:
                #        if len(data) == 0:
                #                self.cli.close()
                #                self.cli = None
                #                return None
                #        return data
                if self.cli == None:
                        return None
                if select.select([self.cli], [], [], 0.01)[0]:
                        try:
                                data = self.cli.recv(1024)
                        except socket.error, e:
                                if e.errno == 32: # borken pipe, cli disconnected
                                        self.cli = None

                                return None
                        else:
                                return data
                else:
                        return None


        def cliSend(self, st):
                st = st + b'\r\n'
                print 'sending: ' + st
                if self.cli == None:
                        return
                try:
                        self.cli.sendall(st)
                except socket.error, e:
                        if e.errno == 32: # borken pipe, cli disconnected
                                self.cli = None


        def localPrompt(self):
                if select.select([self.cmd_hdlr.inf], [], [], 0.01)[0]:
                        line = self.cmd_hdlr.inf.readline()
                        if not line:
                                return
                        cmd = cmd_line._arg_split(line.strip())
                        self.cliSend(str(cmd[:]))
                        self.cmd_hdlr.doCmd(cmd[0], cmd[1:])

        def remotePrompt(self):
                cmd = self.cliRead()
                if cmd == None:
                        return
                cmd = cmd_line._arg_split(cmd.strip())
                self.cliSend(str(cmd[:]))
                self.cmd_hdlr.doCmd(cmd[0], cmd[1:])


        def do(self):
                # self.logger.debug('accepting...')
                self.cliAccept()
                # self.logger.debug('local prompt')
                self.localPrompt()
                # self.logger.debug('remote prompt')
                self.remotePrompt()
                # self.logger.debug('trying tick')
                if self.fw != None and self.fw_run:
                        # self.logger.debug('tick!')
                        self.fw.doTick()
                time.sleep(0.5)



###
# CODE
###
