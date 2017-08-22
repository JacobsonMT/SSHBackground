#!/usr/bin/python

"""
NAME
  ssh_background.py - Terminator plugin to apply a host-dependant background image

DESCRIPTION
  This plugin monitors the most recent line that contains a hostname on each 
  terminator terminal, and applies a host-specific profile if the hostname is 
  changed. 

PROMPT MATCHING
  The plugin simply parses the most recent lines and matches them against 
  a provided regex "[^@]+@(\w+)" ((e.g. user@host) to find hostname.
  
PROFILE MATCHING
  Once an hostname is found, the plugin tries to match it against the given
  image names.

INSTALLATION
  
  Put this .py in /usr/share/terminator/terminatorlib/plugins/ssh_background.py 
  or ~/.config/terminator/plugins/ssh_background.py.

  Then modify the configuration in .config/terminator/config to specify, at least,
  the images glob.

CONFIGURATION

  Plugin section in .config/terminator/config :
  [plugins]
    [[SSHBackground]]
  
  Configuration keys :
  - images glob : glob syntax for images used as backgrounds for matching hosts
    REQUIRED
    key : images
    value : a string. Ex. '/home/XXX/pictures/backgrounds/*.png'

  - prompt patterns : for prompt matching
    key : patterns
    value : a regex list. Default if not set : "[^@]+@(\w+)" (e.g. user@host)
    E.g :
    patterns = "[^@]+@(\w+):([^#]+)#", "[^@]+@(\w+) .+ \$"
    
  - failback profile : profile if no matching image is found
    key : failback_profile
    value : a string. Default if not set : 'default'

EXAMPLE CONFIGURATION
...
[plugins]
  [[SSHBackground]]
    images = /home/XXX/pictures/backgrounds/*.png
    patterns = ^\w+@(\w+)
  ...
...
   
DEVELOPMENT
  Development resources for the Python Terminator class and the 'libvte' Python 
  bindings can be found here:

  For terminal.* methods, see: 
    - http://bazaar.launchpad.net/~gnome-terminator/terminator/trunk/view/head:/terminatorlib/terminal.py
    - and: apt-get install libvte-dev; less /usr/include/vte-0.0/vte/vte.h

  For terminal.get_vte().* methods, see:
    - https://github.com/linuxdeepin/python-vte/blob/master/python/vte.defs
    - and: apt-get install libvte-dev; less /usr/share/pygtk/2.0/defs/vte.defs

DEBUGGING
  To debug the plugin, start Terminator from another terminal emulator 
  like this:

     $ terminator --debug-classes=SSHBackground

"""

import re
import terminatorlib.plugin as plugin

from terminatorlib.util import err, dbg
from terminatorlib.terminator import Terminator
from terminatorlib.config import Config
from collections import OrderedDict

import glob
import os

try:
    import pynotify
    # Every plugin you want Terminator to load *must* be listed in 'AVAILABLE'
    # This is inside this try so we only make the plugin available if pynotify
    #  is present on this computer.
    AVAILABLE = ['SSHBackground']
except ImportError:
    err(_('SSHBackground plugin unavailable'))


class SSHBackground(plugin.Plugin):
    watches = {}
    config = {}
    capabilities = ['ssh_background']
    patterns = []
    failback_profile = 'default'

    def __init__(self):
        self.config = Config().plugin_get_config(self.__class__.__name__)
        self.watches = {}

        self.images = self.load_images()
        dbg(self.images)

        global_config = Terminator().config
        # Create ssh profiles
        self.ssh_profiles = {}
        for f in glob.glob(self.images):
            dbg(f)
            name = os.path.splitext(os.path.basename(f))[0]
            self.ssh_profiles[name] = f
            global_config.add_profile(name)
            profile = global_config.base.profiles[name]
            profile["background_darkness"] = 0.88
            profile["background_image"] = f
            profile["background_type"] = "image"

        dbg(repr(self.ssh_profiles))

        for v in global_config.list_profiles():
            dbg(repr(v))

        self.failback_profile = self.get_failback()
        self.last_profile = self.failback_profile
        self.load_patterns()
        self.update_watches()

    def update_watches(self):
        for terminal in Terminator().terminals:
            if terminal not in self.watches:
                self.watches[terminal] = terminal.get_vte().connect('contents-changed', self._on_terminal_change, terminal)

    def _on_terminal_change(self, _, terminal):
        self.update_watches()

        hostname = self.get_recent_hostname(terminal)
        hostname = hostname if hostname in self.ssh_profiles else self.failback_profile
        if hostname != self.last_profile:
            dbg("setting profile " + hostname)
            terminal.set_profile(None, hostname, False)
            self.last_profile = hostname

        return True

    def _on_user_input(self, _, data, size, terminal):
        self.update_watches()
        if (data == '\r'):
            dbg("Enter")
            hostname = self.get_recent_hostname(terminal)
            hostname = hostname if hostname in self.ssh_profiles else self.failback_profile
            if hostname != self.last_profile:
                dbg("setting profile " + hostname)
                terminal.set_profile(None, hostname, False)
                self.last_profile = hostname
            else:
                dbg("No change.")
        # return True

    def get_recent_hostname(self, terminal, max_depth=2):
        """Retrieve recent hostname of terminal (contains 'user@hostname')"""
        vte = terminal.get_vte()

        cursor = vte.get_cursor_position()
        column_count = vte.get_column_count()
        row_position = cursor[1]

        start_row = row_position
        start_col = 0
        end_row = row_position
        end_col = column_count

        for i in xrange(max_depth + 1):
            if start_row - i < 0:
                break
            line = vte.get_text_range(start_row - i, start_col, end_row - i, end_col, lambda a, b, c, d: True)
            hostname = self.parse_hostname(line)
            if hostname:
                return hostname
        return None

    def parse_hostname(self, hostline):
        for prompt_pattern in self.patterns:
            match = prompt_pattern.match(hostline)
            if match:
                hostname = match.group(1)
                return hostname
        return None

    def load_images(self):

        if self.config and 'images' in self.config:
            return self.config['images']
        else:
            return ""

    def load_patterns(self):

        if self.config and 'patterns' in self.config:
            if isinstance(self.config['patterns'], list):
                for pat in self.config['patterns']:
                    self.patterns.append(re.compile(pat))
            else:
                self.patterns.append(re.compile(self.config['patterns']))
        else:
            self.patterns.append(re.compile(r"[^@]+@(\w+)"))

    def get_failback(self):
        """ failback profile, applies if profile not found. """

        if self.config and 'failback_profile' in self.config:
            return self.config['failback_profile']
        else:
            return 'default'
