"""
This module provides a quick n dirty way to get a debug ipython shell.
2 ways to achieve that:

1. call set_trace() will immediately stop your program at that position
2. import ipdb will overwrite sys.excepthook with ipdb.info. This will
   provide the ipython shell
"""

import sys
from IPython.core.debugger import Pdb
from IPython.core.shellapp import InteractiveShellApp
from IPython.core import ipapi

shell = InteractiveShellApp(argv=[''])

def_colors = ipapi.get().colors

def set_trace():
    frame = sys._getframe().f_back
    Pdb(def_colors).set_trace(frame)

# Post-Mortem interface, copied from pdb
def post_mortem(t=None):
    # handling the default
    if t is None:
        # sys.exc_info() returns (type, value, traceback) if an exception is
        # being handled, otherwise it returns None
        t = sys.exc_info()[2]
        if t is None:
            raise ValueError("A valid traceback must be passed if no "
                                               "exception is being handled")
    # added def_colors here for ipython colors
    p = Pdb(def_colors)
    #p.reset()
    p.interaction(None, t)

# code snippet from http://code.activestate.com/recipes/65287-automatically-start-the-debugger-on-an-exception/
def info(type, value, tb):
    if hasattr(sys, 'ps1') or not sys.stderr.isatty():
        # we are in interactive mode or we don't have a tty-like
        # device, so we call the default hook
        sys.__excepthook__(type, value, tb)
    else:
        import traceback
        # we are NOT in interactive mode, print the exception...
        traceback.print_exception(type, value, tb)
        print
        # ...then start the debugger in post-mortem mode.
        # pdb.pm() does pdb.post_mortem
        post_mortem(sys.last_traceback)

sys.excepthook = info