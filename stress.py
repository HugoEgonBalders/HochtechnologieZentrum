"""
This file contains the PyAIML stress test.  It creates two bots, and connects
them in a cyclic loop.  A lot of output is generated; piping the results to
a log file is highly recommended.
"""

import aiml

# Create the kernels
kern1 = aiml.Kernel()
kern2 = aiml.Kernel()

# Initialize the kernels
print("Initializing Kernel #1")
kern1.bootstrap(learn_file_paths="sets/std-startup.xml", commands="load aiml b")
kern1.save_brain("standard.brn")
print("\nInitializing Kernel #2")
kern2.bootstrap(brain_file_path="standard.brn")

# Start the bots off with some basic input.
response = "askquestion"

# Off they go!
while True:
    response = kern1.respond(response).strip()
    print("1:", response)
    response = kern2.respond(response).strip()
    print("2:", response)
    # If the robots have run out of things to say, force one of them
    # to break the ice.
    if response == "":
        response = "askquestion"
