#!/usr/bin/env python3

# This file is Copyright (c) 2020 Phuong Dang <phuongminh.xxxx@gmail.com>
# License: BSD

import argparse

from migen import *

from custom_boards.platforms import at7core
from litex.build.xilinx.vivado import vivado_build_args, vivado_build_argdict

from litex.soc.cores.clock import *
from litex.soc.integration.soc_core import *
from litex.soc.integration.soc_sdram import *
from litex.soc.integration.builder import *

# CRG ----------------------------------------------------------------------------------------------

class _CRG(Module):
    def __init__(self, platform, sys_clk_freq):
        self.clock_domains.cd_por       = ClockDomain()
        self.clock_domains.cd_sys       = ClockDomain()

        # POR implementation
        clk50     = platform.request("clk50")
        cpu_reset = platform.request("cpu_reset")

        self.reset_delay = Signal(max=4095, reset=4095)
        self.reset = Signal()

        self.comb += self.cd_por.clk.eq(clk50)

        self.sync.por += [
            If(~cpu_reset,
                self.reset_delay.eq(4095)
            ).Elif(self.reset_delay != 0,
                self.reset_delay.eq(self.reset_delay - 1)
            ),
            self.reset.eq(self.reset_delay != 0)
        ]

        self.submodules.pll = pll = S7PLL(speedgrade=-2)
        self.comb += pll.reset.eq(self.reset)
        pll.register_clkin(clk50,            int(50e6))
        pll.create_clkout(self.cd_sys,       int(1*sys_clk_freq))

        # Important, this ensures the system works properly
        platform.add_period_constraint(clk50, 20)
        platform.add_period_constraint(self.cd_sys.clk, float(1e9/sys_clk_freq))
        # platform.add_platform_command("set_property CLOCK_DEDICATED_ROUTE FALSE [get_nets clk50_IBUF]")

# BaseSoC ------------------------------------------------------------------------------------------

class BaseSoC(SoCCore):
    def __init__(self, sys_clk_freq=int(20e6), with_ethernet=False, with_etherbone=False, **kwargs):
        platform = at7core.Platform()

        # SoCCore ----------------------------------------------------------------------------------
        SoCCore.__init__(self, platform, clk_freq=sys_clk_freq, csr_data_width=32, **kwargs)

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = _CRG(platform, sys_clk_freq)

# Build --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteX SoC on XC7A100T core board")
    builder_args(parser)
    soc_sdram_args(parser)
    vivado_build_args(parser)
    parser.add_argument("--with-etherbone", action="store_true", help="enable Etherbone support")
    args = parser.parse_args()

    soc = BaseSoC(with_ethernet=False, with_etherbone=False,
        **soc_sdram_argdict(args))
    builder = Builder(soc, **builder_argdict(args))
    builder.build(**vivado_build_argdict(args))


if __name__ == "__main__":
    main()
