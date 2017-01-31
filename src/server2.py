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
import struct
import os
import sys
import fcntl
import time
import select

import cmd_line

###
# PRIVATE VARIABLES and FUNCTIONS
###

# taken from so: http://stackoverflow.com/questions/11735821/python-get-localhost-ip
# user credit: sloth
def _get_interface_ip(ifname):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', ifname[:15]))[20:24])


def _getLocalIp():
        ip = 'localhost'
        try:
                ip = socket.gethostbyname(socket.gethostname())
        except socket.error, e:
                interfaces = [
                        'eth0',
                        'eth1',
                        'eth2',
                        'wlan0',
                        'wlan1',
                        'wifi0',
                        'ath0',
                        'ath1',
                        'ppp0',
                ]

                for ifname in interfaces:
                        try:
                                ip = _get_interface_ip(ifname)
                                break
                        except IOError:
                                pass
                return ip
        else:
                return ip

###
# CLASSES
###
class Server:

        CONNECTION_BUFFER_LEN = 1024
        BROADCAST_RATE = 1000

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

        class CommandFWDeselect(cmd_line.Command):

                def __init__(self, hdlr, server):
                        cmd_line.Command.__init__(self, hdlr)
                        self.server = server

                def do(self, argv):
                        self.hdlr.doCmd('fwselect', [])

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
                self.my_ip = str(_getLocalIp())
                self.my_port = str(port)
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

                self.bc_dest = '<broadcast>'
                self.bc_port = 11112
                self.bc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.bc.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

                self.last_time = int(time.time() * 1000)
                self.broadcast = True

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
                        if e.errno == 35 or e.errno == 11:
                                return
                        else:
                                print e
                        return


        def cliRead(self):
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
                # broadcast ip and port to other devices every 5 seconds
                curr_time = int(1000 * time.time())
                if self.broadcast and curr_time - self.last_time >= Server.BROADCAST_RATE and not self.cliIsConn():
                        self.bc.sendto('main_brain_super_server>' + self.my_port + '<', (self.bc_dest, self.bc_port))
                        self.last_time = curr_time
                self.cliAccept()
                self.localPrompt()
                self.remotePrompt()
                if self.fw != None and self.fw_run:
                        self.fw.doTick()
                time.sleep(0.05)



###
# CODE
###
