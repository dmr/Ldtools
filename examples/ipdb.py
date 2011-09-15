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




#===============================================================================
# # http://code.activestate.com/recipes/52215/
#
# import sys, traceback
#
# def print_exc_plus():
#    """
#    Print the usual traceback information, followed by a listing of all the
#    local variables in each frame.
#    """
#    tb = sys.exc_info()[2]
#    while 1:
#        if not tb.tb_next:
#            break
#        tb = tb.tb_next
#    stack = []
#    f = tb.tb_frame
#    while f:
#        stack.append(f)
#        f = f.f_back
#    stack.reverse()
#    traceback.print_exc()
#    print "Locals by frame, innermost last"
#    for frame in stack:
#        print
#        print "Frame %s in %s at line %s" % (frame.f_code.co_name,
#                                             frame.f_code.co_filename,
#                                             frame.f_lineno)
#        for key, value in frame.f_locals.items():
#            print "\t%20s = " % key,
#            #We have to be careful not to cause a new error in our error
#            #printer! Calling str() on an unknown object could cause an
#            #error we don't want.
#            try:
#                print value
#            except:
#                print "<ERROR WHILE PRINTING VALUE>"
#
#
# if __name__ == '__main__':
#    #A simplistic demonstration of the kind of problem this approach can help
#    #with. Basically, we have a simple function which manipulates all the
#    #strings in a list. The function doesn't do any error checking, so when
#    #we pass a list which contains something other than strings, we get an
#    #error. Figuring out what bad data caused the error is easier with our
#    #new function.
#
#    data = ["1", "2", 3, "4"] #Typo: We 'forget' the quotes on data[2]
#    def pad4(seq):
#        """
#        Pad each string in seq with zeros, to four places. Note there
#        is no reason to actually write this function, Python already
#        does this sort of thing much better.
#        Just an example.
#        """
#        return_value = []
#        for thing in seq:
#            return_value.append("0" * (4 - len(thing)) + thing)
#        return return_value
#
#    #First, show the information we get from a normal traceback.print_exc().
#    try:
#        pad4(data)
#    except:
#        traceback.print_exc()
#    print
#    print "----------------"
#    print
#
#    #Now with our new function. Note how easy it is to see the bad data that
#    #caused the problem. The variable 'thing' has the value 3, so we know
#    #that the TypeError we got was because of that. A quick look at the
#    #value for 'data' shows us we simply forgot the quotes on that item.
#    try:
#        pad4(data)
#    except:
#        print_exc_plus()
#===============================================================================
