"""
    Output a rising-edge pulse from the AnalogDiscovery2.
    User inputs:
        channel out 
        number of packets to send
        frequency
"""

from ctypes import *
from dwfconstants import *
import sys

dwf = None

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


class AnalogDiscoveryUtils:

    def __init__(self, sample_rate, num_samples_to_acquire):
        self.sample_rate = sample_rate
        self.num_samples_to_acquire = num_samples_to_acquire
        self.interface_handler = None
        self.internal_clock_freq = None

    def open_device(self):
        """Opens the connection to AD2. 
        Sets the class attribute post-connection dwf interface_handler object, as well as the internal clock frequency.
        """
        #open device
        #declare ctype variables
        hdwf = c_int()
        sts = c_byte()

        print "Opening first device"
        dwf.FDwfDeviceOpen(c_int(-1), byref(hdwf))

        if hdwf.value == 0:
            print "failed to open device"
            quit()

        self.interface_handler = hdwf

        hzSys = c_double()
        dwf.FDwfDigitalOutInternalClockInfo(ad_utils.interface_handler, byref(hzSys))
        self.internal_clock_freq = hzSys
        print " internal frequency is " + str(hzSys.value)


    def close_device(self):
        """Close the connection to AD2."""
        dwf.FDwfDeviceCloseAll()
        print "device closed"    


    def run(ad_utils):
        """The main function of the experiment.
        Our test harness consists of two parts:
            -constant frequency digital output to trigger openmote pin 
            -logic analyzer to sample input channels to AD, and save values to a csv file.
        """

        # in record mode samples after trigger are acquired only
        dwf.FDwfDigitalInAcquisitionModeSet(hdwf, acqmodeRecord)
        # sample rate = system frequency / divider, 100MHz/100 = 1 MHz
        #dwf.FDwfDigitalInDividerSet(hdwf, c_int(100))

if __name__ == "__main__":

    num_packets = int(raw_input("Number of packets to send: "))
    period = int(raw_input("Duration between packets (in ms): "))
    sample_rate = int(raw_input("Logic Analyzer sampling rate: "))

    experiment_duration = (num_packets * period) / 1000

    nSamples = experiment_duration * sample_freq

    print "duration: " + str(experiment_duration)
    print "number of sample: " + str(nSamples)

    startup()

    ad_utils = AnalogDiscoveryUtils(sample_rate, nSamples)
    ad_utils.open_device()
    #run(ad_utils)
    #ad_utils.close_device()



