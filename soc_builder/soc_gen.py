#!/usr/bin/env python3
import os
import sys
import math
import struct

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.build.generic_platform import *
from litex.build.xilinx import XilinxPlatform

from litex.soc.cores.clock import *
from litex.soc.integration.soc_core import *

from litex.soc.integration.builder import *
from litex.soc.interconnect import csr_bus
from litex.soc.cores.uart import *

def get_common_ios():
    return [
        # clk / rst
        ("clk100", 0, Pins("E3"), IOStandard("LVCMOS33")),
        ("rst", 0, Pins("C2"), IOStandard("LVCMOS33")),

        ("serial", 0,
            Subsignal("tx", Pins("D10")),
            Subsignal("rx", Pins("A9")),
            IOStandard("LVCMOS33")
        ),
    ]

class Platform(XilinxPlatform):
    def __init__(self):
        XilinxPlatform.__init__(self, "xc7a35ticsg324-1L", io=[], toolchain="vivado")

class CRG(Module):
    def __init__(self, platform, soc_config):
        self.clock_domains.cd_sys = ClockDomain()
        self.clock_domains.cd_sys2x = ClockDomain(reset_less=True)
        self.clock_domains.cd_sys2x_dqs = ClockDomain(reset_less=True)
        self.clock_domains.cd_iodelay = ClockDomain()

        # # #

        clk = platform.request("clk100")
        rst = platform.request("rst")

        self.submodules.sys_pll = sys_pll = S7PLL(speedgrade=soc_config["speedgrade"])
        self.comb += sys_pll.reset.eq(rst)
        sys_pll.register_clkin(clk, soc_config["input_clk_freq"])
        sys_pll.create_clkout(self.cd_sys, soc_config["sys_clk_freq"])
        sys_pll.create_clkout(self.cd_sys2x, 2*soc_config["sys_clk_freq"])
        sys_pll.create_clkout(self.cd_sys2x_dqs, 2*soc_config["sys_clk_freq"], phase=90)
        #self.comb += platform.request("pll_locked").eq(sys_pll.locked)

        self.submodules.iodelay_pll = iodelay_pll = S7PLL()
        self.comb += iodelay_pll.reset.eq(rst)
        iodelay_pll.register_clkin(clk, soc_config["input_clk_freq"])
        iodelay_pll.create_clkout(self.cd_iodelay, soc_config["iodelay_clk_freq"])
        self.submodules.idelayctrl = S7IDELAYCTRL(self.cd_iodelay)

class BaseSoC(SoCCore):
    csr_map = {
        "ctrl":   0,
        "uart":   2,
        "timer0": 3,
    }
    interrupt_map = {
        "uart":   3,
        "timer0": 4,
    }
    mem_map = {
        "rom":    0x00000000,
        "sram":   0x10000000,
        "csr":    0xf0000000,
    }
    csr_map.update(SoCCore.csr_map)
    interrupt_map.update(SoCCore.interrupt_map)

    def __init__(self, platform, soc_config, **kwargs):
        platform.add_extension(get_common_ios())
        sys_clk_freq = soc_config["sys_clk_freq"]
        SoCCore.__init__(self, platform, sys_clk_freq,
                         with_uart=True,
                         integrated_main_ram_size=0,
                         **kwargs)
        # crg
        self.submodules.crg = CRG(platform, soc_config)

def main():
    # get config
    if len(sys.argv) < 2:
        print("missing config file")
        exit(1)
    exec(open(sys.argv[1]).read(), globals())

    # generate core
    platform = Platform()
    soc = BaseSoC(platform, soc_config,
                  ident=soc_config["ident"],
                  integrated_rom_size=soc_config["rom_size"],
                  integrated_sram_size=soc_config["sram_size"],
                  cpu_type=soc_config["cpu"],
                  cpu_variant=soc_config["cpu_variant"]
                  )

    output_dir = "build/" + soc_config["soc_name"]
    build_name = soc_config["soc_name"] + "_core"

    builder = Builder(soc, output_dir=output_dir , compile_gateware=True)
    vns = builder.build(build_name=build_name, regular_comb=False)

    # prepare core (could be improved)
    def replace_in_file(filename, _from, _to):
        # Read in the file
        with open(filename, "r") as file :
            filedata = file.read()

        # Replace the target string
        filedata = filedata.replace(_from, _to)

        # Write the file out again
        with open(filename, 'w') as file:
            file.write(filedata)

    init_filename = "mem.init"
    os.system("mv " + output_dir + "/gateware/mem.init " + output_dir + "/gateware/" + build_name + ".init".format(init_filename))
    replace_in_file(output_dir + "/gateware/" + build_name + ".v", init_filename, build_name + ".init")

if __name__ == "__main__":
    main()
