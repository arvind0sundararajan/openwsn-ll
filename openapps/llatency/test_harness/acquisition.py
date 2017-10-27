"""
	Latency recording script for AnalogDiscovery2

	User inputs:
		1. Number of networks
		2. AD2 channels in each network
		3. Number of packets in each network

	Output:
		1. Records data to [FILENAME].csv

	Written by Alex Yang and Arvind Sundararajan
	Last modified 10/26/2017.
"""

from ctypes import *
from dwfconstants import *
import sys
import math

dwf = None

# dictionary where (k,v) = (network, [[input_channels], [output_channels]])
network_to_channels = {}

output_channels_to_network = {}
input_channels_to_network = {}


class Network:
	output_channels = []
	input_channels = []
	num_packets = 0

	def __init__(self, output_channels, input_channels, num_packets_to_send):
		self.output_channels = output_channels
		self.input_channels = input_channels
		self.num_packets = num_packets_to_send


class AnalogDiscoveryUtils:
	def __init__(self):
		self.interface_handler = None
		self.internal_digital_out_clock_freq = None
		self.internal_digital_in_clock_freq = None
		self.max_buffer_size_in = c_int()

	def open_device(self):
		"""Opens the connection to AD2.
		   Sets the class attribute post-connection dwf interface_handler
			   object, as well as the internal clock frequency.
		"""
		# open device
		# declare ctype variables
		hdwf = c_int()
		# sts = c_byte()

		print "Opening first device"
		dwf.FDwfDeviceOpen(c_int(-1), byref(hdwf))

		if hdwf.value == 0:
			print "failed to open device"
			quit()

		self.interface_handler = hdwf

		hzSysOut = c_double()
		hzSysIn = c_double()

		dwf.FDwfDigitalOutInternalClockInfo(self.interface_handler, byref(hzSysOut))
		dwf.FDwfDigitalInInternalClockInfo(self.interface_handler, byref(hzSysIn))
		dwf.FDwfDigitalInBufferSizeInfo(self.interface_handler, byref(self.max_buffer_size_in))
		self.internal_digital_out_clock_freq = hzSysOut
		self.internal_digital_in_clock_freq = hzSysIn
		print "internal digital out frequency is " + str(hzSysOut.value)
		print "internal digital in frequency is " + str(hzSysIn.value)
		print "digital in max buffer size: " + str(self.max_buffer_size_in.value)

	def close_device(self):
		"""Close the connection to AD2."""
		dwf.FDwfDeviceCloseAll()
		print "device closed"

	def run(self, network):
		"""The main function of the experiment.
		Our test harness consists of two parts:
			-digital output to trigger openmote pin. the output rising edge is 1 ms after the reception is high
			-logic analyzer to sample input channels to AD, and save values to a csv file.

		Script workflow:
		(Python): trigger rising edge on DIO 0.
		(AD2): start sampling at 1 MHz. sample until packet received rising edge. (triggers sampling stop)
		(Python): copy samples (contents of buffer) to memory. postprocess: remove redundant samples (only save samples that change 0-1)
		(Python): write these samples to file
		(Python): increment number of packets sent
		repeat above steps until number of packets sent = number of packets in experiment
		"""

		##### DIGITAL OUT SETUP
		# enable output on network input channels
		digital_out_channels_bits = 0
		for channel in network.input_channels:
			digital_out_channels_bits = digital_out_channels_bits | (1<<channel)
		dwf.FDwfDigitalIOOutputEnableSet(self.interface_handler, c_int(digital_out_channels_bits))
		##### END DIGITAL OUT SETUP

		enabled_outputs = c_uint32()
		dwf.FDwfDigitalIOOutputEnableGet(self.interface_handler, byref(enabled_outputs))
		#print enabled DIO outputs as bitfield (32 digits, removing 0b at the front)
		print "Enabled Digital IO Pins:  " + bin(enabled_outputs.value)[2:].zfill(32)

		##### DIGITAL IN SETUP
		sampling_rate = int(self.internal_digital_in_clock_freq.value / 100)  # 1 MHz sample rate

		# approximate number of samples assuming ~500ms latency per packet
		nSamples = 1500000
		# array to hold data
		rgwSamples = (c_uint16 * nSamples)()
		cAvailable = c_int()
		cLost = c_int()
		cCorrupted = c_int()
		cSamples = 0
		fLost = 0
		fCorrupted = 0

		# TODO: figure out which acquisition mode is best, record or single
		# in record mode samples after trigger are acquired only
		dwf.FDwfDigitalInAcquisitionModeSet(self.interface_handler, acqmodeRecord)

		# set clock divider to sampling rate
		dwf.FDwfDigitalInDividerSet(self.interface_handler, c_int(sampling_rate))
		# take 16 bits per sample
		dwf.FDwfDigitalInSampleFormatSet(self.interface_handler, c_int(16))

		# set buffer size as large as we can
		dwf.FDwfDigitalInBufferSizeSet(self.interface_handler, self.max_buffer_size_in)

		# take as many samples as possible after trigger to fill up buffer
		dwf.FDwfDigitalInTriggerPositionSet(self.interface_handler, c_int(nSamples))

		# set trigger source to AD2 digital in channels
		dwf.FDwfDigitalInTriggerSourceSet(self.interface_handler, trigsrcDetectorDigitalIn)

		# set DigitalIn trigger on button press channel rising edge
		digital_in_trigger_channels_bits = (1 << network.output_channels[0])
		dwf.FDwfDigitalInTriggerSet(self.interface_handler, c_int(0), c_int(0), c_int(digital_in_trigger_channels_bits),
									c_int(0))

		##### END DIGITAL IN SETUP

		num_packets_received = 0
		last_packet_received = True

		status = c_byte()
		dio_pins = c_uint32()
		button_press_high = c_int(1 << (network.output_channels[0]))
		packet_sent_high = c_int(1 << (network.output_channels[1]))
		packet_received_high = c_int((1 << network.output_channels[-1]))

		while num_packets_received <= network.num_packets:
			# start acquisition acquisition
			dwf.FDwfDigitalInConfigure(self.interface_handler, c_bool(0), c_bool(1))
			print "begin acquisition"

			# reset cSamples
			cSamples = 0

			while cSamples < nSamples:
				if last_packet_received == True:
					# we can send the next packet because the last packet was received
					# button press! set value on enabled AD2 output pins (digital_out_channels_bits)
					# AD2 output is wired to button press input which triggers acquisition
					dwf.FDwfDigitalIOOutputSet(self.interface_handler, c_int(digital_out_channels_bits))

					dwf.FDwfDigitalInStatus(self.interface_handler, c_int(1), byref(status))
					print "button pressed; status = {}".format(status)

					last_packet_received = False
					#set digital out back low
					dwf.FDwfDigitalIOOutputSet(self.interface_handler, c_int(0))

				# fetch digital IO information from the device
				dwf.FDwfDigitalIOStatus(self.interface_handler)
				# read state of all pins, regardless of output enable
				dwf.FDwfDigitalIOInputStatus(self.interface_handler, byref(dio_pins))
				#print "Digital IO Pins:  " + bin(dio_pins.value)[2:].zfill(32)

				if (dio_pins.value & packet_received_high.value) == packet_received_high.value:
					# packet received, stop sampling
					dwf.FDwfDigitalInConfigure(self.interface_handler, c_bool(0), c_bool(0))
					num_packets_received += 1
					print "received packet {}".format(num_packets_received)
					last_packet_received = True

				dwf.FDwfDigitalInStatusRecord(self.interface_handler, byref(cAvailable), byref(cLost), byref(cCorrupted))

				cSamples += cLost.value

				if cLost.value:
					fLost = 1
				if cCorrupted.value:
					fCorrupted = 1
				if cAvailable.value == 0:
					#print "no samples available"
					continue
				if cSamples + cAvailable.value > nSamples:
					cAvailable = c_int(nSamples - cSamples)

				#print "available, lost, corrupted samples: {}, {}, {}".format(cAvailable.value, cLost.value, cCorrupted.value)
				# copy samples to computer
				dwf.FDwfDigitalInStatusData(self.interface_handler, byref(rgwSamples, 2*cSamples), c_int(2*cAvailable.value))
				cSamples += cAvailable.value

				if last_packet_received == True:
					break
			
			print "about to call postprocess"	
			self.postprocess(rgwSamples, "data.csv")
			rgwSamples = (c_uint16 * nSamples)()

		print "Done with experiment"
		return

	def postprocess(self, data, data_file):
		"""TODO: remove redundant samples
		only save samples where value changes from 0 to 1 or 1 to 0
		"""
		print "processing"
		with open(data_file, 'a') as f:
			for v in data:
				f.write("%s\n" % v)
		f.close()


def initialize_networks(num_networks):
	""" Initializes all networks """

	# keep asking for networks
	for number in range(num_networks):
		print "Network {}:".format(number)
		print "If entering multiple values, please separate them with commas and a space."
		print "Example: 2, 3, 4\n"

		print "Network output channels: channels to measure network. These are digital inputs to AD2."
		print "Format: button press channel, packet sending confirmation channel, packet reception channel"
		output_channels = raw_input("   Network output channels: ")

		print "Network input channels: digital IO channel which is the button press. This is a digital output from AD2."
		print "Only one channel can be a network input channel."
		input_channels = raw_input("   Network input channels: ")

		# convert channels from string of comma separated ints to list of ints
		output_channels = [int(i) for i in output_channels.split(", ")]
		input_channels = [int(i) for i in input_channels.split(", ")]

		for channel in output_channels:
			assert 0 <= channel < 16
		for channel in input_channels:
			assert 0 <= channel < 16

		num_packets_to_send = input("   Number of packets to send: ")

		# create new network
		network = Network(output_channels, input_channels, num_packets_to_send)

		# add to (network)->[[input_channels], [output_channels]] dictionary
		network_to_channels[network] = [input_channels, output_channels]

		# add to (output channel)->(network) dictionary
		for channel in output_channels:
			output_channels_to_network[channel] = network

		# add to (input channel)->(network) dictionary
		for channel in input_channels:
			input_channels_to_network[channel] = network


if __name__ == "__main__":
	if sys.platform.startswith("win"):
		dwf = cdll.dwf
	elif sys.platform.startswith("darwin"):
		dwf = cdll.LoadLibrary("/Library/Frameworks/dwf.framework/dwf")
	else:
		dwf = cdll.LoadLibrary("libdwf.so")

	# print DWF version
	version = create_string_buffer(16)
	dwf.FDwfGetVersion(version)
	print "DWF Version: " + version.value

	num_networks = input("Number of networks: ")
	initialize_networks(num_networks)

	ad_utils = AnalogDiscoveryUtils()
	ad_utils.open_device()

	for network in network_to_channels:
		ad_utils.run(network)

	ad_utils.close_device()
