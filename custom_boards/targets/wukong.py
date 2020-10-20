#!/usr/bin/env python3

# This file is Copyright (c) 2015-2019 Florent Kermarrec <florent@enjoy-digital.fr>
# License: BSD

import argparse

from migen import *

from custom_boards.platforms import wukong
from litex.build.xilinx.vivado import vivado_build_args, vivado_build_argdict

from litex.soc.cores.clock import *
from litex.soc.integration.soc_core import *
from litex.soc.integration.soc_sdram import *
from litex.soc.integration.builder import *

from litedram.modules import MT41K128M16
from litedram.phy import s7ddrphy

from liteeth.phy.mii import LiteEthPHYMII

# CRG ----------------------------------------------------------------------------------------------

class _CRG(Module):
    def __init__(self, platform, sys_clk_freq):
        self.clock_domains.cd_por       = ClockDomain()
        self.clock_domains.cd_sys       = ClockDomain()
        self.clock_domains.cd_sys2x     = ClockDomain(reset_less=True)
        self.clock_domains.cd_sys4x     = ClockDomain(reset_less=True)
        self.clock_domains.cd_sys4x_dqs = ClockDomain(reset_less=True)
        self.clock_domains.cd_clk200    = ClockDomain()
        self.clock_domains.cd_eth       = ClockDomain()

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
        # pll.create_clkout(self.cd_sys2x,     int(2*sys_clk_freq))
        # pll.create_clkout(self.cd_sys4x,     int(4*sys_clk_freq))
        # pll.create_clkout(self.cd_sys4x_dqs, int(4*sys_clk_freq), phase=90)
        # pll.create_clkout(self.cd_clk200,    int(200e6))
        # pll.create_clkout(self.cd_eth,       int(25e6))

        # self.submodules.idelayctrl = S7IDELAYCTRL(self.cd_clk200)

        # Important, this ensures the system works properly
        platform.add_period_constraint(clk50, 20)
        platform.add_period_constraint(self.cd_sys.clk, float(1e9/sys_clk_freq))
        # platform.add_period_constraint(self.cd_sys2x.clk, float(1e9/(2*sys_clk_freq)))
        # platform.add_period_constraint(self.cd_sys4x.clk, float(1e9/(4*sys_clk_freq)))
        # platform.add_period_constraint(self.cd_sys4x_dqs.clk, float(1e9/(4*sys_clk_freq)))
        # platform.add_period_constraint(self.cd_clk200.clk, float(1e9/200e6))
        # platform.add_period_constraint(self.cd_eth.clk, float(1e9/25e6))
        platform.add_platform_command("set_property CLOCK_DEDICATED_ROUTE FALSE [get_nets clk50_IBUF]")

# BaseSoC ------------------------------------------------------------------------------------------

class BaseSoC(SoCCore):
    def __init__(self, sys_clk_freq=int(100e6), with_ethernet=False, with_etherbone=False, **kwargs):
        platform = wukong.Platform()

        # SoCCore ----------------------------------------------------------------------------------
        SoCCore.__init__(self, platform, clk_freq=sys_clk_freq, csr_data_width=32, **kwargs)

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = _CRG(platform, sys_clk_freq)

        # DDR3 SDRAM -------------------------------------------------------------------------------
        # if not self.integrated_main_ram_size:
            # self.submodules.ddrphy = s7ddrphy.A7DDRPHY(platform.request("ddram"),
                # memtype        = "DDR3",
                # nphases        = 4,
                # sys_clk_freq   = sys_clk_freq,
                # interface_type = "MEMORY")
            # self.add_csr("ddrphy")
            # self.add_sdram("sdram",
                # phy                     = self.ddrphy,
                # module                  = MT41K128M16(sys_clk_freq, "1:4"),
                # origin                  = self.mem_map["main_ram"],
                # size                    = kwargs.get("max_sdram_size", 0x40000000),
                # l2_cache_size           = kwargs.get("l2_size", 8192),
                # l2_cache_min_data_width = kwargs.get("min_l2_data_width", 128),
                # l2_cache_reverse        = True
            # )

# Build --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteX SoC on Wukong board")
    builder_args(parser)
    soc_sdram_args(parser)
    vivado_build_args(parser)
    parser.add_argument("--with-ethernet", action="store_true", help="enable Ethernet support")
    parser.add_argument("--with-etherbone", action="store_true", help="enable Etherbone support")
    args = parser.parse_args()

    soc = BaseSoC(with_ethernet=False, with_etherbone=False,
        **soc_sdram_argdict(args))
    builder = Builder(soc, **builder_argdict(args))
    builder.build(**vivado_build_argdict(args))


if __name__ == "__main__":
    main()
