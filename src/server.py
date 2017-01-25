#!/usr/bin/env python

##
# @file         server.py
# @author       Manuel Federanko
# @version      0.0.0-r1
# @since        16-11-29
#
# @brief        A small class for telnet servers.
#               This server provides a small ABC for creating more complex server structures.
#
# It has 4 commands preinstalled: start, stop, exit and kick
# It should be obvious what those commands do.
# The exit command stops the server if it is not already stopped.
##


#
# IMPORTS
#
import socket
import abc
import threading
import re
import logger
from cmd_line import *

#
# PRIVATE VARIABLES and FUNCTIONS
#


#
# CLASSES
#

##
# The Server class provides an ABC for a simple telnet server.
class Server:
        __metaclass__ = abc.ABCMeta

        ##
        # Starts the Server.
        class CommandServerStart(Command):

                def __init__(self, hndlr, server):
                        Command.__init__(self, hndlr)
                        self.server = server

                def do(self, argv):
                        self.server.start()

        ##
        # Stops the Server.
        class CommandServerStop(Command):

                def __init__(self, hndlr, server):
                        Command.__init__(self, hndlr)
                        self.server = server

                def do(self, argv):
                        if self.server.running and self.server.should_run:
                                self.server.stop()

        ##
        # Kicks the connected client from the Server.
        class CommandServerKick(Command):

                def __init__(self, hndlr, server):
                        Command.__init__(self, hndlr)
                        self.server = server

                def do(self, argv):
                        self.server.disconnect()

        ##
        # Exits the server (and stops it in the process).
        class CommandServerExit(Command):

                def __init__(self, hndlr, server):
                        Command.__init__(self, hndlr)
                        self.server = server

                def do(self, argv):
                        self.hndlr.doCmd('stop')



        ##
        # Creates a server listening on port <port> and providing a simple terminal-like CmdHandler, which, by default, listens on stdin and writes to stdout/stderr
        # The server listens for only 1 connection at a time and registers 4 default commands:
        #  - start ... starts the server
        #  - stop  ... stops the server
        #  - kick  ... kicks the currently connected client
        #  - exit  ... stops the server (if necessary) and exits
        # @param port           the port to listen on
        # @param cmdhdlr        the handler for the server
        def __init__(self, port, logger, cmdhdlr):
                self.logger = logger

                self.cmdhandler = cmdhdlr
                self.cmdhandler.regCmd('start', Server.CommandServerStart(self.cmdhandler, self))
                self.cmdhandler.regCmd('stop' ,Server.CommandServerStop(self.cmdhandler, self))
                self.cmdhandler.regCmd('kick' ,Server.CommandServerKick(self.cmdhandler, self))
                self.cmdhandler.overrideCmd('exit', Server.CommandServerExit(self.cmdhandler, self))

                # the server
                self.logger.info('creating server socket...')
                self.socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.logger.info('done')

                self.logger.info('binding to port: ' + str(port) + '...')
                try:
                        self.socket_server.bind(('', port))
                except socket.error, exc:
                        self.logger.err('fail')
                self.logger.info('done')

                self.socket_server.listen(1)

                # the client conn
                self.socket_connection = None
                self.socket_connection_infile = None
                self.should_run = False
                self.running = False
                self.thread = None

        ##
        # Returns True if a client is connected to the server, otherwise False
        # @returns      True if a client is connected, otherwise False
        def connected(self):
                return self.socket_connection != None and self.socket_connection_infile != None

        ##
        # Accepts the next connection.
        def accept(self):
                if self.connected():
                        return

                self.logger.info('accepting client connection...')
                self.socket_connection, addr = self.socket_server.accept()
                self.socket_connection_infile = self.socket_connection.makefile("r+")
                self.logger.info('done')

        ##
        # Kicks the currently connected client.
        def disconnect(self):
                if self.connected():
                        self.logger.info('kicking client...')
                        self.socket_connection_infile.close()
                        self.socket_connection_infile = None
                        try:
                                self.socket_connection.shutdown(2)
                        except socket.error, exc:
                                pass
                        self.socket_connection.close()
                        self.socket_connection = None
                        self.logger.info('done')

        ##
        # Reads some data from the connection and strips the trailing NL and/or LF.
        # @returns      the received line of data
        def read_from_conn(self):
                if not self.connected():
                        return None

                line = self.socket_connection_infile.readline()
                if len(line) == 0:
                        self.disconnect()
                        return None

                self.logger.debug('received data: ' + line)
                return line.strip()

        ##
        # Writes a string to the connected cleint, appending CRNL.
        # @param st     the string to write
        def write_to_conn(self, st):
                if not self.connected():
                        return
                self.socket_connection.sendall(st)
                self.socket_connection.sendall(b'\r\n')

        ##
        # Runs the server, accepting, handling and disconnecting clients in a loop.
        def run(self):
                self.running = True

                while self.should_run:
                        self.accept()
                        while self.should_run and self.connected():
                                line = self.read_from_conn()
                                if line != None:
                                        self.doAction(line)

                self.running = False

        ##
        # Starts the server, a Thread is created which runs the self.run method.
        def start(self):
                self.logger.info('starting server...')
                self.should_run = True
                self.thread = threading.Thread(target=self.run)
                self.thread.start()
                self.logger.info('done')

        ##
        # Connects a dummy client to the server and sends some data, in order to release the lockup from the accept call, if no client is connected to the server.
        def dummystop(self):
                if self.connected():
                        self.disconnect()
                
                try:
                        dummycli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        dummycli.connect(('localhost', self.socket_server.getsockname()[1]))
                        dummycli.send('DUMMYQUIT')
                        dummycli.close()
                except socket.error, exc:
                        pass

        ##
        # Stops the server.
        # This is done by setting the run-flag to False and waiting until the server has disconnected.
        # In parallel there is a Thread spawn, which connects the dummyclient to the server to release the accept lock.
        def stop(self):
                self.logger.info('stopping server...')
                if self.thread != None:
                        self.should_run = False
                        threading.Thread(target=self.dummystop).start()
                        self.thread.join()
                self.socket_server.close()
                self.logger.info('done')


        ##
        # This method is called as soon as data is received.
        # @param line   the data received
        @abc.abstractmethod
        def doAction(self, line):
                pass

class DummyServer(Server):

        LVL_CHAT = logger.LoggingLevel(1, '\033[1;36m' + 'CHAT' + logger.CCODES.ENDC)
        LVL_REPL = logger.LoggingLevel(1, '\033[1;35m' + 'REPL' + logger.CCODES.ENDC)

        def doAction(self, line):
                DefaultLogger.log(DummyServer.LVL_CHAT, line)

        def tell(self, line):
                DefaultLogger.log(DummyServer.LVL_REPL, line)
                self.write_to_conn(line)
#
# CODE
#