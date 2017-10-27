"""
	Latency recording script for AnalogDiscovery2

	User inputs:
		1. Number of networks
		2. AD2 channels in each network
		3. Number of packets in each network

	Output:
		1. Records data to [FILENAME].csv

	Written by Alex Yang and Arvind Sundararajan
	10/26/2017.
"""

from ctypes import *
from dwfconstants import *
import sys
from time import gmtime, strftime

dwf = None

# list of networks
list_of_networks = []

class Network:
	output_channels = []
	input_channels = []
	num_packets = 0

	output_channels_bit_rep = 0
	input_channels_bit_rep = 0

	def __init__(self, output_channels, input_channels, num_packets_to_send):
		self.output_channels = output_channels
		self.input_channels = input_channels
		self.num_packets = num_packets_to_send

class AnalogDiscoveryUtils:

	def __init__(self):
		self.interface_handler = None
		self.internal_digital_in_clock_freq = None
		self.max_buffer_size_in = c_int()

		# bit representations of the AD2 DIO channels
		# index is 1 if that pin is included in input/output
		self.input_channels_bit_rep = 0
		self.output_channels_bit_rep = 0

		# boolean that keeps track of AD2's DIO interface with network
		self.network_added = False

	def open_device(self):
		"""Opens the connection to AD2.
		   Sets the class attribute post-connection dwf interface_handler
			   object, as well as the internal clock frequency.
		"""
		# open device
		# declare ctype variables
		hdwf = c_int()

		print "Opening first device"
		dwf.FDwfDeviceOpen(c_int(-1), byref(hdwf))

		if hdwf.value == 0:
			print "failed to open device"
			quit()

		self.interface_handler = hdwf

		hzSysIn = c_double()

		dwf.FDwfDigitalInInternalClockInfo(self.interface_handler, byref(hzSysIn))
		dwf.FDwfDigitalInBufferSizeInfo(self.interface_handler, byref(self.max_buffer_size_in))
		self.internal_digital_in_clock_freq = hzSysIn
		print "internal digital in frequency is " + str(hzSysIn.value)
		print "digital in max buffer size: " + str(self.max_buffer_size_in.value)

	def close_device(self):
		"""Resets instruments and closes the connection to AD2."""
		
		# reset DigitalIO instrument
		dwf.FDwfDigitalIOReset()

		#reset DigitalIn instrument
		dwf.FDwfDigitalInReset(ad_utils.interface_handler)

		dwf.FDwfDeviceCloseAll()
		print "device closed"

	def add_network(self, network):
		"""sets network outputs to be AD2 input channels
		sets all other AD2 channels to be outputs. 
		this is done to control AD2 outputs and keep them constant
		"""
		for channel in network.output_channels:
			self.input_channels_bit_rep = self.input_channels_bit_rep | (1<<channel)

		# every channel that is not a network input channel is an AD output
		self.output_channels_bit_rep = ((2 ** 16) - 1) ^ self.input_channels_bit_rep

		self.network_added = True

		print "AD2 input channels: {}".format(bin(self.input_channels_bit_rep))
		print "AD2 output channels: {}\n".format(bin(self.output_channels_bit_rep))

	def _get_DIO_values(self, print_vals=False):
		"""Returns an int containing the DIO channel values.
		"""
		dio_pins = c_uint16()
		# fetch digital IO information from the device
		dwf.FDwfDigitalIOStatus(self.interface_handler)
		# read state of all pins, regardless of output enable
		dwf.FDwfDigitalIOInputStatus(self.interface_handler, byref(dio_pins))
		if print_vals:
			print "Digital IO Pins:  " + bin(dio_pins.value)[2:]
		return dio_pins.value

	def _configure_DigitalIO(self):
		"""configure the DigitalIO instrument for the experiment."""

		# this is to see that we can set DIO inputs/outputs according to the network inputs/outputs
		assert self.network_added == True

		# reset DigitalIO instrument
		dwf.FDwfDigitalIOReset()

		# enable AD DIO output channels (every channel that is not a network output channel) to be an output
		dwf.FDwfDigitalIOOutputEnableSet(self.interface_handler, c_int(self.output_channels_bit_rep))

		enabled_outputs = c_uint32()
		dwf.FDwfDigitalIOOutputEnableGet(self.interface_handler, byref(enabled_outputs))
		#print enabled DIO outputs as bitfield (32 digits, removing 0b at the front)
		print "enabled digital output pins:  " + bin(enabled_outputs.value)[2:]

		# set all enabled outputs to zero
		dwf.FDwfDigitalIOOutputSet(self.interface_handler, c_uint16(0))
		return

	def _configure_DigitalIn(self, num_samples, trigger_channel_bit_rep):
		"""configure DigitalIn instrument for the experiment.
		Samples at 1 MHz.
		Configures the trigger when the channel represented by trigger_channel_bit_rep is high.
		Configures instrument to take num_samples to take after trigger. 

		NOTE: both arguments are ints, not c_int()
		"""

		#reset DigitalIn instrument
		dwf.FDwfDigitalInReset(self.interface_handler)

		# in record mode samples after trigger are acquired only
		dwf.FDwfDigitalInAcquisitionModeSet(self.interface_handler, acqmodeRecord)
		# set clock divider; we want to sample at 100 MHz / 100 = 1 MHz
		dwf.FDwfDigitalInDividerSet(self.interface_handler, c_int(100))
		# take 16 bits per sample
		dwf.FDwfDigitalInSampleFormatSet(self.interface_handler, c_int(16))

		# set buffer size as large as we can
		#dwf.FDwfDigitalInBufferSizeSet(self.interface_handler, self.max_buffer_size_in)

		# take num_samples after trigger
		dwf.FDwfDigitalInTriggerPositionSet(self.interface_handler, c_uint32(num_samples))
		# set trigger source to AD2 DigitalIn channels
		dwf.FDwfDigitalInTriggerSourceSet(self.interface_handler, trigsrcDetectorDigitalIn)
		# set DigitalIn trigger when trigger_channel_bit_rep is high
		dwf.FDwfDigitalInTriggerSet(self.interface_handler, c_int(0), c_int(trigger_channel_bit_rep), c_int(0), c_int(0))

		#printing miscellaneous trigger info

		current_trigger_source = c_ubyte()
		dwf.FDwfDigitalInTriggerSourceGet(self.interface_handler, byref(current_trigger_source))
		print "Current trigger source: {}\n".format(current_trigger_source)

		trigger_position_configured = c_uint()
		dwf.FDwfDigitalInTriggerPositionGet(self.interface_handler, trigger_position_configured)
		print "Configured trigger position: {}\n".format(trigger_position_configured)

		trigger_detector_low = c_uint()
		trigger_detector_high = c_uint()
		trigger_detector_rising = c_uint()
		trigger_detector_falling = c_uint()
		dwf.FDwfDigitalInTriggerGet(self.interface_handler, byref(trigger_detector_low), byref(trigger_detector_high), 
			byref(trigger_detector_rising), byref(trigger_detector_falling))
		print "Configured trigger detector option"
		print "low: {}".format(trigger_detector_low)
		print "high: {}".format(trigger_detector_high)
		print "rising: {}".format(trigger_detector_rising)
		print "falling: {}\n".format(trigger_detector_falling)

		# start acquisition; should wait for trigger
		dwf.FDwfDigitalInConfigure(self.interface_handler, c_bool(0), c_bool(1))

		return

	def test(self, network):
		"""Miscellaneous testing."""
		self._configure_DigitalIO()

		enabled_outputs = c_uint32()

		dwf.FDwfDigitalIOOutputEnableGet(self.interface_handler, byref(enabled_outputs))
		#print enabled DIO outputs as bitfield (32 digits, removing 0b at the front)
		print "enabled digital output pins:  " + bin(enabled_outputs.value)[2:].zfill(32)

		print "outputting on every output"
		for i in range(16):
			output = c_uint16(1<<i)
			dwf.FDwfDigitalIOOutputSet(self.interface_handler, output)
			self._get_DIO_values(print_vals=True) 
		return
		
	def run(self, network):
		"""The main function of the experiment.
		Our test harness consists of two parts:
			-digital output to trigger openmote pin. the output rising edge is 1 ms after the reception is high
			-logic analyzer to sample input channels to AD, and save values to a csv file.
		Script workflow:
		(Python): trigger rising edge on DIO 0.
		(AD2): start sampling at 1 MHz. sample until packet received rising edge. stop sampling.
		(Python): continuously copy samples (contents of buffer) to memory. 
		once packet is received:
		(Python) postprocess: remove redundant samples (only save samples that change 0-1)
		(Python): write these samples to file
		(Python): increment number of packets sent
		repeat above steps until number of packets sent = number of packets in experiment
		"""
		experiment_start_time = strftime("%H_%M_%S_%m_%d_%Y", gmtime())
		print "starting at {}".format(experiment_start_time)


		# relevant bits of AD output
		button_press_bit = 1 << network.input_channels[0]

		#relevant bits of AD inputs
		# note that button_press_mirror_bit is an AD input while button_press_bit is an AD output
		button_press_mirror_bit = 1 << network.output_channels[0]
		packet_created_bit = 1 << network.output_channels[1]
		packet_received_bit = 1 << network.output_channels[-1]
		bits_to_monitor = (button_press_mirror_bit| packet_created_bit | packet_received_bit)

		print "button_press_mirror: {}".format(bin(button_press_mirror_bit))
		print "packet_created: {}".format(bin(packet_created_bit))
		print "packet_received: {}".format(bin(packet_received_bit))
		print "bits_to_monitor: {}".format(bin(bits_to_monitor))


		##### SAMPLING STUFF SETUP #####
		# approximate number of samples assuming ~500ms latency per packet
		nSamples = 1500000
		# array to hold data
		rgwSamples = (c_uint16 * nSamples)()
		cAvailable = c_int()
		cLost = c_int()
		cCorrupted = c_int()

		num_packets_received = 0
		packets_missed = 0
		num_packets_total = network.num_packets
		last_packet_received = True
		##### END SAMPLING STUFF #####


		# reset and configure DigitalIO
		self._configure_DigitalIO()

		# reset and configure DigitalIn to take nSamples on trigger
		# set DigitalIn trigger when button_press_mirror_bit channel is raised (this should start sampling)
		self._configure_DigitalIn(nSamples, button_press_mirror_bit)


		##### MAIN LOOP of experiment. #####
		# runs for the duration of the experiment

		while num_packets_received < num_packets_total:
			print "begin acquisition {}".format(num_packets_received + 1)

			# set cSamples (count of samples taken so far) to 0
			cSamples = 0

			# inner loop: runs from button press until packet received.
			while cSamples < nSamples:
				if last_packet_received == True:
					# we can send the next packet because the last packet was received
					# button press -> set value on enabled AD2 output pins (digital_out_channels_bits)
					# AD2 output is wired to button press input which triggers acquisition
					dwf.FDwfDigitalIOOutputSet(self.interface_handler, c_uint16(button_press_bit))
					print "button pressed"
					self._get_DIO_values(print_vals=True)

					last_packet_received = False
					#set all digital out channels back low
					dwf.FDwfDigitalIOOutputSet(self.interface_handler, c_uint16(0))
					self._get_DIO_values(print_vals=True)

				# we have to manually stop sampling once packet_received_bit is raised
				curr_DIO = self._get_DIO_values()
				if ((curr_DIO & packet_received_bit) == packet_received_bit):
					# packet received, stop sampling
					dwf.FDwfDigitalInConfigure(self.interface_handler, c_bool(0), c_bool(0))
					num_packets_received += 1
					print "received packet {}".format(num_packets_received)
					last_packet_received = True

				# record info about the data collection process
				dwf.FDwfDigitalInStatusRecord(self.interface_handler, byref(cAvailable), byref(cLost), byref(cCorrupted))

				cSamples += cLost.value

				#if cAvailable.value == 0:
					#print "no samples available"
					#continue
				if cSamples + cAvailable.value > nSamples:
					cAvailable = c_int(nSamples - cSamples)

				#print "available: {}, lost: {}, corrupted: {}".format(cAvailable.value, cLost.value, cCorrupted.value)
				# copy samples to rgwSamples on computer
				dwf.FDwfDigitalInStatusData(self.interface_handler, byref(rgwSamples, 2*cSamples), c_int(2*cAvailable.value))
			
				if last_packet_received == True:
					break

				cSamples += cAvailable.value

			# reach here if packet was received OR if 1.5 million samples have been taken
			if last_packet_received == True:
				self.postprocess(num_packets_received, rgwSamples, bits_to_monitor, "data_" + experiment_start_time + ".csv")
			else:
				# we took 1.5 million samples and missed the packet
				packets_missed += 1

				# set last_packet_received to True to try button press again
				last_packet_received = True

			# clear rgwSamples for next packet
			rgwSamples = (c_uint16 * nSamples)()

			#reset, configure DigitalIO for next packet
			self._configure_DigitalIO()

			#reset, configure DigitalIn for next packet
			self._configure_DigitalIn(nSamples, button_press_mirror_bit)

		print "Done with experiment"
		return

	def postprocess(self, packet_number, data, bits_to_save, data_file):
		"""Only write values to file where any one of the bits enabled in bits_to_save changes.
		The data saved is an integer with ith bit = 1 if ith channel was high, bit = 0 if channel was low
		"""
		print "postprocessing {}\n".format(packet_number)
		with open(data_file, 'a') as f:
			"""
			f.write("Packet {}\n".format(packet_number))
			sample_index, prev_sample = 0, 0
			for sample in data:
				#xor keeps a bit if it is different
				if ((prev_sample ^ sample) & bits_to_save) != 0:
					f.write("{}, {}\n".format(sample_index, sample))

				sample_index += 1
				prev_sample = sample
			"""
			f.write("Packet {}\n".format(packet_number))
			for sample in data:
				print "sample datatype: {}".format(type(sample))
				f.write("{}\n".format(sample))
		return


def initialize_networks(num_networks):
	""" Initializes all networks """

	# keep asking for networks
	for number in range(num_networks):
		print "Network {}:".format(number)
		print "If entering multiple values, please separate them with commas and a space."
		print "Example: 2, 3, 4\n"

		print "Network output channels: channels to measure network. These are digital inputs to AD2."
		print "Format: [button press channel], [packet creation channel], [packet reception channel]"
		output_channels = raw_input("   Network output channels: ")

		print "\nNetwork input channels: digital IO channel which is the button press. This is a digital output from AD2."
		print "For 1-1 case: only one channel can be a network input channel."
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

		# add to global array of networks
		list_of_networks.append(network)


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

	try:
		for network in list_of_networks:
			ad_utils.add_network(network)
			#ad_utils.test(network)
			ad_utils.run(network)
	except KeyboardInterrupt:
		dwf.FDwfDigitalIOReset(ad_utils.interface_handler)
		ad_utils.close_device()
		sys.exit(1)

	ad_utils.close_device()
	sys.exit(0)