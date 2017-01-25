#!/usr/bin/env python

##
# @file         cmd_line.py
# @author       Manuel Federanko
# @version      0.0.0-r1
# @since        16-11-29
#
# @brief        A small command-line interface, which makes it simpler to run commands.
##

#
# IMPORTS
#
import sys
import abc
import time

#
# PRIVATE VARIABLES and FUNCTIONS
#

##
# Splits a command line input, much like bash on spaces (' '). The Escape character is a backslash ('\').
# the resulting array is returned
# @param line   the line to split
# @returns      the split array
#
def _arg_split(line):
        quo = False
        esc = False
        res = ['']
        for i in range(0, len(line)):
                x = line[i]

                if not esc and x == '\\':
                        esc = True
                        continue
                if esc:
                        res[-1] += x
                        esc = False
                        continue
                if x == ' ':
                        if len(res[-1]) > 0:
                                res.append('')
                        continue

                res[-1] += x
        return res

#
# CLASSES
#

##
# The ABC Command is a generic way of executing code when entering a command.
# The do method gets the arguments passed and the self.hndlr object directs to the overlying CmdHandler object.
class Command:
        __metaclass__ = abc.ABCMeta

        ##
        # Init the Command with the handler and a override array (in theory there doesn't need to be an array, but it works and is not crucial to fix)
        def __init__(self, hndlr):
                self.hndlr = hndlr
                self.ovrride = []

        ##
        # The workflow to execute when entering a command
        # @param argv   the arguments passed to the command
        @abc.abstractmethod
        def do(self, argv):
                pass

        ##
        # This method is called after the self.do method, to call all overridden commands
        def ov(self):
                for cmd in self.ovrride:
                        cmd.do([])

##
# The CmdHandler handles user input to create a simple terminal like prompt.
# It registers two default commands: exit and list
# The exit command exits the prompt and the list command lists all registered commands
class CmdHandler:

        ##
        # Exits the command-line.
        class CommandExit(Command):

                def do(self, argv):
                        self.hndlr.looping = False

        ##
        # Lists all commands known by this command line.
        class CommandList(Command):

                def do(self, argv):
                        for key in sorted(self.hndlr.cmds.keys()):
                                if self.hndlr.outf != None:
                                        self.hndlr.outf.write(' ' + key + '\n')
                                        self.hndlr.outf.flush()


        ##
        # Inits the CmdHandler with a name and an input-, output- and error file descriptor.
        # The default commands are registered.
        # @param name   then name of the CmdHandler
        # @param infile         the input file descriptor
        # @param outfile        the output file descriptor
        # @param errfile        the error file descriptor
        def __init__(self, name = '', infile = sys.stdin, outfile = sys.stdout, errfile = sys.stderr):
                self.name = name
                self.inf = infile
                self.outf = outfile
                self.errf = errfile
                self.cmds = {}
                self.looping = True

                self.cmds['exit'] = CmdHandler.CommandExit(self)
                self.cmds['list'] = CmdHandler.CommandList(self)

        ##
        # Registeres a command and replaces all previously registered ones.
        # @param name   then name under which to register the command
        # @param cmd    the command to register
        def regCmd(self, name, cmd):
                self.cmds[name] = cmd

        ##
        # Overrides the specified command, appends the old command to the override list of the new one
        # and regsiters the new command.
        # @param name   the name under which to register the command
        # @param cmd    the new command
        def overrideCmd(self, name, cmd):
                if name in self.cmds:
                        cmd.ovrride.append(self.cmds[name])

                self.regCmd(name, cmd)

        ##
        # Executes a command.
        # @param cmd    the name of the command, the command object the gets retrieved from the registry
        # @param argv   the arguments passed to the command
        def doCmd(self, cmd, argv = []):
                if cmd in self.cmds:
                        cmd_ = self.cmds[cmd]
                        cmd_.do(argv)
                        cmd_.ov()
                else:
                        if self.errf != None:
                                self.errf.write('no such command\n')

        ##
        # Prompts the user for input in the form of: `self.name>` and executes the command.
        def prompt(self):
                if self.outf != None:
                        self.outf.write(self.name + '> ')
                        self.outf.flush()
                if self.inf != None:
                        while True:
                                line = self.inf.readline().strip()
                                if len(line) > 0:
                                        break;
                                time.sleep(0.1)
                        cmd = _arg_split(line)
                        self.doCmd(cmd[0], cmd[1:])

        ##
        # Runs the CmdHandler.
        # The handler should only be run over this method, writing your own loop for that will break the exit command.
        def run(self):
                while self.looping:
                        self.prompt()

#
# CODE
#
# A default CmdHandler which reads from stdin and writes to stdout/stderr
DefaultCmdHandler = CmdHandler()