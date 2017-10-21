"""
    Latency recording script for AnalogDiscovery2

    User inputs:
        1. Number of networks
        2. AD2 channels in each network
        3. Number of packets in each network

    Output:
        1. Records data to [FILENAME].csv
"""

from ctypes import *
from dwfconstants import *
import sys
import math

dwf = None
output_channels_to_network = {}
input_channels_to_network = {}

class Network:
    output_channels = [] 
    input_channels = []
    packets_remaining = 0

    def __init__(self, output_channels, input_channels, packets_remaining):
        self.output_channels = list(output_channels)
        self.input_channels = list(input_channels)
        self.packets_remaining = packets_remaining


class AnalogDiscoveryUtils:
    def __init__(self):
        self.interface_handler = None
        self.internal_clock_freq = None


def initialize_networks(num_networks):
    """ Initializes all networks """

    # keep asking for networks
    for number in range(num_networks):
        print("Network {}:".format(number))
        output_channels = input("   Sending mote channels: ")
        input_channels = input("    Receiving mote channels: ")
        num_packets_to_send = input ("    Number of packets to send: ")

        # create new network 
        network = Network(output_channels, input_channels, num_packets_to_send)

        # add to (output channel)->(network) dictionary
        for channel in output_channels:
            output_channels_to_network[channel] = network

        # add to (input channel)->(network) dictionary
        for channel in input_channels:
            input_channels_to_network[channel] = network

def startup():
    """ Sets the global dwf variable to the appropriate value. Runs on program startup.
    """
    if sys.platform.startswith("win"):
        dwf = cdll.dwf
    elif sys.platform.startswith("darwin"):
        dwf = cdll.LoadLibrary("/Library/Frameworks/dwf.framework/dwf")
    else:
        dwf = cdll.LoadLibrary("libdwf.so")

    #print DWF version
    version = create_string_buffer(16)
    dwf.FDwfGetVersion(version)
    print "DWF Version: "+version.value 

if __name__ == "__main__":
    
    num_networks = input("Number of networks: ")
    initialize_networks(num_networks)
    startup()



