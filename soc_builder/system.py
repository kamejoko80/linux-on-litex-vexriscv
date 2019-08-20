#!/usr/bin/env python3
import os
import sys
import math
import struct

from migen import *
import basys3

class System(Module):
    def __init__(self, platform):
        serial = platform.request("serial")
        clk = platform.request("clk")

        # SoC_01
        self.specials += Instance("soc_core",
            o_serial_tx=serial.tx1,
            i_serial_rx=serial.rx1,
            i_clk100=clk,
        )
        # SoC_02
        self.specials += Instance("soc_core",
            o_serial_tx=serial.tx2,
            i_serial_rx=serial.rx2,
            i_clk100=clk,
        )
        # SoC_03
        self.specials += Instance("soc_core",
            o_serial_tx=serial.tx3,
            i_serial_rx=serial.rx3,
            i_clk100=clk,
        )
        # SoC_04
        self.specials += Instance("soc_core",
            o_serial_tx=serial.tx4,
            i_serial_rx=serial.rx4,
            i_clk100=clk,
        )
        # SoC_05
        self.specials += Instance("soc_core",
            o_serial_tx=serial.tx5,
            i_serial_rx=serial.rx5,
            i_clk100=clk,
        )
        # SoC_06
        self.specials += Instance("soc_core",
            o_serial_tx=serial.tx6,
            i_serial_rx=serial.rx6,
            i_clk100=clk,
        )
        # SoC_07
        self.specials += Instance("soc_core",
            o_serial_tx=serial.tx7,
            i_serial_rx=serial.rx7,
            i_clk100=clk,
        )

        platform.add_source(os.path.join("build/soc/gateware", "soc_core.v"))
        platform.add_source(os.path.join("build/soc/gateware", "soc_core.init"))
        platform.add_source(os.path.join("build/soc/gateware", "mem_1.init"))
        platform.add_source(os.path.join("build/soc/gateware", "mem_2.init"))
        platform.add_source(os.path.join("../litex/litex/soc/cores/cpu/vexriscv/verilog", "VexRiscv_Min.v"))

platform = basys3.Platform()
dut = System(platform)
platform.build(dut)       