"""Cli commands in MPF."""
import argparse
from importlib import import_module
import os
import sys
from pkg_resources import iter_entry_points


import mpf.core
from mpf._version import version

EXAMPLES_FOLDER = 'examples'
CONFIG_FOLDER = 'config'


class CommandLineUtility(object):

    """Default cli entry point."""

    def __init__(self, path=None):
        """Initialise cli entry point."""
        self.argv = sys.argv[:]
        self.path = path
        self.mpf_path = os.path.abspath(os.path.join(mpf.core.__path__[0],
                                                     os.pardir))
        self.external_commands = dict()
        self.get_external_commands()

    def get_external_commands(self):
        """Entry point to hook more commands.

        This is used from mpf mc.
        """
        for entry_point in iter_entry_points(group='mpf.command', name=None):
            command, function = entry_point.load()()
            self.external_commands[command] = function

    @classmethod
    def check_python_version(cls):
        """Check that we have at least python 3."""
        if sys.version_info[0] != 3:
            print("MPF requires Python 3. You have Python {}.{}.{}".format(
                sys.version_info[0], sys.version_info[1], sys.version_info[2]
            ))
            sys.exit()

    def execute(self):
        """Actually run the command that was just set up."""
        self.check_python_version()

        commands = set()

        for file in os.listdir(os.path.join(self.mpf_path, 'commands')):
            commands.add(os.path.splitext(file)[0])

        command = 'game'

        if len(self.argv) > 1:

            if self.argv[1] in self.external_commands:
                command = self.argv.pop(1)
                return self.external_commands[command](self.mpf_path,
                                                       *self.parse_args())
            elif self.argv[1] in commands:
                command = self.argv.pop(1)

        module = import_module('mpf.commands.%s' % command)

        machine_path, remaining_args = self.parse_args()

        module.Command(self.mpf_path, machine_path, remaining_args)

    def parse_args(self):
        """Parse arguments."""
        parser = argparse.ArgumentParser(description='MPF Command')

        parser.add_argument("machine_path", help="Path of the machine folder.",
                            default=None, nargs='?')

        parser.add_argument("--version",
                            action="version", version=version,
                            help="Displays the MPF, config file, and BCP "
                                 "version info and exits")

        # the problem with parser.add_argument is it will take the first
        # positional argument it finds for machine_path and set it to the
        # machine path, regardless of what's in front of it. So for example,
        # args of "-c step4" will lead to machine_path='step4', but that's not
        # right, machine_path should be None. But this is because it doesn't
        # know that -c wants to consume the next positional arg.

        # So our workaround is we check if there are any argv, and if so, we
        # check to see if the first one starts with a dash, meaning it's an
        # optional arg and guaranteeing that whatever's after it is NOT our
        # machine path, so in that case, we just insert a None as the machine
        # path in front of it and everything is cool.

        if len(self.argv) > 1 and self.argv[1].startswith('-'):
            self.argv.insert(1, None)

        args, remaining_args = parser.parse_known_args(self.argv[1:])
        machine_path = self.get_machine_path(args.machine_path)

        return machine_path, remaining_args

    def get_machine_path(self, machine_path_hint):
        """Return machine path."""
        machine_path = None

        if machine_path_hint:
            if os.path.isdir(os.path.join(self.path, machine_path_hint)):
                # If the path hint resolves to a folder, use that as the
                # machine folder
                machine_path = os.path.join(self.path, machine_path_hint)

            else:
                # If the folder is invalid, see if we have an examples machine
                # folder with that name
                example_machine_path = os.path.abspath(os.path.join(
                    self.mpf_path, os.pardir, EXAMPLES_FOLDER,
                    machine_path_hint))

                if os.path.isdir(example_machine_path):
                    machine_path = example_machine_path

        else:
            # no path hint passed.
            # Is there a /config folder in our current folder? If so we assume
            # the current folder is the machine folder
            if os.path.isdir(os.path.join(self.path, CONFIG_FOLDER)):
                machine_path = self.path

        if machine_path:
            return machine_path
        else:
            print("Error. Could not find machine folder: '{}'.".format(
                machine_path_hint))
            sys.exit()


def run_from_command_line(args=None):
    """Run cli command."""
    del args
    path = os.path.abspath(os.path.curdir)
    CommandLineUtility(path).execute()
