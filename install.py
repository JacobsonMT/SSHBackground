#!/usr/bin/env python

import os
import glob
import apt
import fileinput
from shutil import copyfile
import sys


def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")

if __name__ == "__main__":
    """
    Install simpsons ssh
    """

    if not query_yes_no("Are you sure you want to install Simpsons SSH Backgrounds? This will modify ~/.config/terminator/config!"):
        quit()

    cache = apt.Cache()
    cache.open()
    if not cache["terminator"].is_installed:
        print "Please install Terminator first; sudo apt-get install terminator"
        quit()

    # Install plugin
    plugin = os.path.expanduser("~/.config/terminator/plugins/ssh_background.py")
    if not os.path.exists(os.path.dirname(plugin)):
        try:
            os.makedirs(os.path.dirname(plugin))
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise
    copyfile('ssh_background.py', plugin)

    # Alter config file

    config_location = os.path.expanduser('~/.config/terminator/config')

    if not os.path.exists(config_location):
        copyfile('config_base', config_location)

    f = open(config_location, "r")
    contents = f.readlines()
    f.close()

    new_contents = []
    enabled_plugins_found = False
    for line in contents:
        new_contents.append(line)
        if line.strip().startswith('enabled_plugins'):
            enabled_plugins_found = True
            new_contents[-1] = new_contents[-1].strip("\n") + ", SSHBackground\n"
        elif line.strip() == '[plugins]':
            new_contents += ['  [[SSHBackground]]\n', '    patterns = "^\w+@(\w+)"\n', '    images = ' + os.path.dirname(os.path.realpath(__file__)) + '/*.png\n']

    if not enabled_plugins_found:
        for i, line in enumerate(new_contents):
            if line.strip() == '[global_config]':
                break

        new_contents.insert(i + 1, "  enabled_plugins = SSHBackground\n")

    f = open(config_location, "w")
    f.writelines(new_contents)
