#!/usr/bin/env python3

# This file is Copyright (c) 2020 Phuong Dang <phuongminh.xxxx@gmail.com>
# License: BSD

import argparse
from fractions import Fraction

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.build.io import DDROutput

from custom_boards.platforms import sp6core

from litex.soc.cores.clock import *
from litex.soc.integration.soc_core import *
from litex.soc.integration.soc_sdram import *
from litex.soc.integration.builder import *

from litedram.modules import AS4C16M16
from litedram.phy import GENSDRPHY

# CRG ----------------------------------------------------------------------------------------------

class _CRG(Module):
    def __init__(self, platform, clk_freq):
        self.clock_domains.cd_sys    = ClockDomain()
        self.clock_domains.cd_sys_ps = ClockDomain(reset_less=True)

        # # #

        self.submodules.pll = pll = S6PLL(speedgrade=-1)
        pll.register_clkin(platform.request("clk32"), 32e6)
        pll.create_clkout(self.cd_sys,    clk_freq)
        pll.create_clkout(self.cd_sys_ps, clk_freq, phase=90)

        # SDRAM clock
        self.specials += DDROutput(1, 0, platform.request("sdram_clock"), ClockSignal("sys_ps"))

# BaseSoC ------------------------------------------------------------------------------------------

class BaseSoC(SoCCore):
    def __init__(self, sys_clk_freq=int(80e6), **kwargs):
        platform = sp6core.Platform(device="xc6slx16")

        # SoCCore ----------------------------------------------------------------------------------
        SoCCore.__init__(self, platform, 
            clk_freq            = sys_clk_freq,
            csr_data_width      = 32,
            **kwargs
        )

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = _CRG(platform, sys_clk_freq)

        # SDR SDRAM --------------------------------------------------------------------------------
        if not self.integrated_main_ram_size:
            self.submodules.sdrphy = GENSDRPHY(platform.request("sdram"))
            self.add_sdram("sdram",
                phy                     = self.sdrphy,
                module                  = AS4C16M16(sys_clk_freq, "1:1"),
                origin                  = self.mem_map["main_ram"],
                size                    = kwargs.get("max_sdram_size", 0x40000000),
                l2_cache_size           = kwargs.get("l2_size", 8192),
                l2_cache_min_data_width = kwargs.get("min_l2_data_width", 128),
                l2_cache_reverse        = True
            )

class SERDESSoC(BaseSoC):
    csr_map = {
        "serwb_master_phy": 20,
        "serwb_slave_phy":  21
    }
    csr_map.update(BaseSoC.csr_map)

    mem_map = {
        "serwb": 0x30000000,
    }
    mem_map.update(BaseSoC.mem_map)

    def __init__(self, platform):

        BaseSoC.__init__(self, platform)

        # serwb enable
        self.comb += platform.request("serwb_enable").eq(1)

        # serwb master
        self.submodules.serwb_master_phy = SERWBLowSpeedPHY(platform.device, platform.request("serwb_master"), mode="master")

        # serwb slave
        self.submodules.serwb_slave_phy = SERWBLowSpeedPHY(platform.device, platform.request("serwb_slave"), mode="slave")

        # leds
        self.comb += [
            platform.request("user_led", 4).eq(self.serwb_master_phy.init.ready),
            platform.request("user_led", 5).eq(self.serwb_master_phy.init.error),
            platform.request("user_led", 6).eq(self.serwb_slave_phy.init.ready),
            platform.request("user_led", 7).eq(self.serwb_slave_phy.init.error),
        ]

        # wishbone slave
        serwb_master_core = SERWBCore(self.serwb_master_phy, self.clk_freq, mode="slave")
        self.submodules += serwb_master_core

        # wishbone master
        serwb_slave_core = SERWBCore(self.serwb_slave_phy, self.clk_freq, mode="master")
        self.submodules += serwb_slave_core

        # wishbone test memory
        self.register_mem("serwb", self.mem_map["serwb"], serwb_master_core.etherbone.wishbone.bus, 8192)
        self.submodules.serwb_sram = wishbone.SRAM(8192, init=[i for i in range(8192//4)])
        self.comb += serwb_slave_core.etherbone.wishbone.bus.connect(self.serwb_sram.bus)

# Build --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteX SoC on Spartan6 Core Board")
    builder_args(parser)
    soc_sdram_args(parser)
    args = parser.parse_args()

    soc = SERDESSoC(**soc_sdram_argdict(args))
    builder = Builder(soc, **builder_argdict(args))
    builder.build()


if __name__ == "__main__":
    main()
