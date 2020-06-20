#!/usr/bin/env python3

import os
import sys

sys.path.append('../')

from migen import *
from litex.soc.cores.clock import *
from litex.build.openocd import OpenOCD
from custom_boards.platforms import wukong

class CRG(Module):
    def __init__(self, platform, sys_clk_freq):
        self.clock_domains.cd_sys = ClockDomain()

        # # #

        self.submodules.pll = pll = S7PLL(speedgrade=-2)
        pll.register_clkin(platform.request("clk50"), 50e6)
        pll.create_clkout(self.cd_sys, sys_clk_freq)

class MyLedBlink(Module):
    def __init__(self, platform):
        self.submodules.crg = CRG(platform, 100e6)
        self.led = led = platform.request("user_led")
        self.rst = rst = platform.request("sw2")

        counter = Signal(25)

        self.sync += [
            If(rst,
                counter.eq(counter + 1)
            ).Else(
                counter.eq(0)
            )
        ]

        self.comb += led.eq(counter[24])

platform = wukong.Platform()
dut = MyLedBlink(platform)
platform.build(dut)

prog = OpenOCD("../prog/openocd_xilinx_platform_cable.cfg")
prog.load_bitstream("build/top.bit")
