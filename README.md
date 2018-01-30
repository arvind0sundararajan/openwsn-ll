# OpenWSN Firmware: Low Latency Wireless Sensor Networks

This repository contains the firmware to conduct low latency experiments with the OpenWSN wireless sensor network.

## How to Use

This project enables sending and receiving radio packets to and from designated motes. For hardware latency measurements, use in conjunction with the [ll-test-harness] project (requires the AnalogDiscovery2).

[ll-test-harness]: https://github.com/arvind0sundararajan/ll-test-harness

0. Required hardware: at least 2 OpenMote-cc2538 devices. Recommended hardware: AnalogDiscovery2, jumpers.

1. Make sure you have the required software dependencies. Build the [vanilla openwsn firmware] and work through the [Kickstart Tutorial] to ensure dependencies work.

[vanilla openwsn firmware]: https://github.com/openwsn-berkeley/openwsn-fw
[Kickstart Tutorial]: https://openwsn.atlassian.net/wiki/spaces/OW/pages/12058660/Get+Started

2. Connect the openmotes to the computer. Note the serial port each mote is connected to. Using the [OpenVisualizer], find the addresses of each OpenMote.

[OpenVisualizer]: https://github.com/openwsn-berkeley/openwsn-sw

3. Build the openwsn-ll firmware on each mote, omitting the `revision` keyword if using the Rev. E OpenMotes:

```
$ sudo scons board=openmote-cc2538 toolchain=armgcc revision=A1 verbose=1 apps='llatency' forcetopology=1 bootload=port1,port2 oos_openwsn
```

4. Modify the last line of `openapps/llatency/llatency_dagroot.py` to set the serial port of the desired dagroot.Run ```$ python openapps/llatency/llatency_dagroot.py``` to set the dagroot and start the network.

## Differences between openwsn-ll and openwsn-fw

* More debugpin functions added in `bsp/boards/openmote-cc2538/debugpins.c`. 

| OpenMote GPIO | Function |
| -------------	| -------- |
| AD0/DIO0 | slot |
| AD1/DIO1 | fsm |
| AD2/DIO2 | task |
| AD3/DIO3 | radio |
| RST/AD6/DIO6 | isr |
| AD5/DIO5 | frame |
| CTS/DIO7 | toggled when llatency packet is received |
| AD4/DIO4 | rising edge interrupt to send packet |
| DO8 | toggled when llatency packet is created |



* `openapps/llatency/`: code to send packets on a dedicated pin interrupt, and raise a dedicate pin on an llatency packet reception
* `openstack/02a-MAClow/topology.c`: a hardcoded topology. For one to one, we have A <-> B <-> C.
* `openstack/02b-MAChigh/schedule.h`: schedule with custom number of active slots. 

## Miscellaneous

* Make sure the same topology in `topology.c` is reflected in the packet destination address defined in `llatency.c`.

OpenWSN firmware: stuff that runs on a mote

Part of UC Berkeley's OpenWSN project, http://www.openwsn.org/.

Build status
------------

|              builder                                                                                                                 |      build                   | outcome
| ------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------- | ------- 
| [Travis](https://travis-ci.org/openwsn-berkeley/openwsn-fw)                                                                          | compile                      | [![Build Status](https://travis-ci.org/openwsn-berkeley/openwsn-fw.png?branch=develop)](https://travis-ci.org/openwsn-berkeley/openwsn-fw)
| [OpenWSN builder](http://builder.openwsn.org/job/Firmware/board=telosb,label=master,project=oos_openwsn,toolchain=mspgcc/)           | compile (TelosB)             | [![Build Status](http://builder.openwsn.org/job/Firmware/board=telosb,label=master,project=oos_openwsn,toolchain=mspgcc/badge/icon/)](http://builder.openwsn.org/job/Firmware/board=telosb,label=master,project=oos_openwsn,toolchain=mspgcc/)
| [OpenWSN builder](http://builder.openwsn.org/job/Firmware/board=gina,label=master,project=oos_openwsn,toolchain=mspgcc/)             | compile (GINA)               | [![Build Status](http://builder.openwsn.org/job/Firmware/board=gina,label=master,project=oos_openwsn,toolchain=mspgcc/badge/icon/)](http://builder.openwsn.org/job/Firmware/board=gina,label=master,project=oos_macpong,toolchain=mspgcc/)
| [OpenWSN builder](http://builder.openwsn.org/job/Firmware/board=wsn430v13b,label=master,project=oos_openwsn,toolchain=mspgcc/)       | compile (wsn430v13b)         | [![Build Status](http://builder.openwsn.org/job/Firmware/board=wsn430v13b,label=master,project=oos_openwsn,toolchain=mspgcc/badge/icon/)](http://builder.openwsn.org/job/Firmware/board=wsn430v13b,label=master,project=oos_macpong,toolchain=mspgcc/)
| [OpenWSN builder](http://builder.openwsn.org/job/Firmware/board=wsn430v14,label=master,project=oos_openwsn,toolchain=mspgcc/)        | compile (wsn430v14)          | [![Build Status](http://builder.openwsn.org/job/Firmware/board=wsn430v14,label=master,project=oos_openwsn,toolchain=mspgcc/badge/icon/)](http://builder.openwsn.org/job/Firmware/board=wsn430v14,label=master,project=oos_macpong,toolchain=mspgcc/)
| [OpenWSN builder](http://builder.openwsn.org/job/Firmware/board=Z1,label=master,project=oos_openwsn,toolchain=mspgcc/)               | compile (Z1)                 | [![Build Status](http://builder.openwsn.org/job/Firmware/board=z1,label=master,project=oos_openwsn,toolchain=mspgcc/badge/icon/)](http://builder.openwsn.org/job/Firmware/board=z1,label=master,project=oos_macpong,toolchain=mspgcc/)
| [OpenWSN builder](http://builder.openwsn.org/job/Firmware/board=OpenMote-CC2538,label=master,project=oos_openwsn,toolchain=armgcc/)  | compile (OpenMote-CC2538)    | [![Build Status](http://builder.openwsn.org/job/Firmware/board=OpenMote-CC2538,label=master,project=oos_openwsn,toolchain=armgcc/badge/icon)](http://builder.openwsn.org/job/Firmware/board=OpenMote-CC2538,label=master,project=oos_openwsn,toolchain=armgcc/)
| [OpenWSN builder](http://builder.openwsn.org/job/Firmware/board=OpenMoteSTM,label=master,project=oos_openwsn,toolchain=armgcc/)      | compile (OpenMoteSTM)        | [![Build Status](http://builder.openwsn.org/job/Firmware/board=openmotestm,label=master,project=oos_openwsn,toolchain=armgcc/badge/icon)](http://builder.openwsn.org/job/Firmware/board=openmotestm,label=master,project=oos_openwsn,toolchain=armgcc/)
| [OpenWSN builder](http://builder.openwsn.org/job/Firmware/board=IoT-LAB_M3,label=master,project=oos_openwsn,toolchain=armgcc/)       | compile (IoT-LAB_M3)         | [![Build Status](http://builder.openwsn.org/job/Firmware/board=iot-lab_M3,label=master,project=oos_openwsn,toolchain=armgcc/badge/icon)](http://builder.openwsn.org/job/Firmware/board=iot-lab_M3,label=master,project=oos_openwsn,toolchain=armgcc/)
| [OpenWSN builder](http://builder.openwsn.org/job/Firmware/board=Python,label=master,project=oos_openwsn,toolchain=gcc/)              | compile (Python, simulation) | [![Build Status](http://builder.openwsn.org/job/Firmware/board=python,label=master,project=oos_openwsn,toolchain=gcc/badge/icon)](http://builder.openwsn.org/job/Firmware/board=python,label=master,project=oos_openwsn,toolchain=gcc/)
| [OpenWSN builder](http://builder.openwsn.org/job/Docs/)                                                                              | publish documentation        | [![Build Status](http://builder.openwsn.org/job/Docs/badge/icon)](http://builder.openwsn.org/job/Docs/)

Documentation
-------------

- overview: https://openwsn.atlassian.net/wiki/
- source code: http://openwsn-berkeley.github.io/firmware/
