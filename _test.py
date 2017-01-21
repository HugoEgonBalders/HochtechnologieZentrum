"""
This script demonstrates how to create a bare-bones, fully functional chatbot using PyAIML.
"""

import sys
import logging

import aiml


logging.basicConfig(level='DEBUG')

# Create a Kernel object.
kern = aiml.Kernel()

# When loading an AIML set, you have two options: load the original
# AIML files, or load a precompiled "brain" that was created from a
# previous run. If no brain file is available, we force a reload of
# the AIML files.
brain_loaded = force_reload = False
while not brain_loaded:
    if force_reload or (len(sys.argv) >= 2 and sys.argv[1] == "reload"):
        # Use the Kernel's bootstrap() method to initialize the Kernel. The
        # optional learnFiles argument is a file (or list of files) to load.
        # The optional commands argument is a command (or list of commands)
        # to run after the files are loaded.
        kern.bootstrap(learn_file_paths="sets/std-startup.xml", commands="load aiml b")
        brain_loaded = True
        # Now that we've loaded the brain, save it to speed things up for
        # next time.
        kern.save_brain("standard.brn")
    else:
        # Attempt to load the brain file.  If it fails, fall back on the Reload
        # method.
        force_reload = True
        #try:
        #    # The optional branFile argument specifies a brain file to load.
        #    kern.bootstrap(brain_file_path="standard.brn")
        #    brain_loaded = True
        #except:
        #    force_reload = True

# Enter the main input/output loop.
print(kern.respond("start"))
while True:
    print(kern.respond(input("> ")))
