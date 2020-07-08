#!/usr/bin/env python3

# This file is Copyright (c) 2020 Phuong Dang <kamejokoxx@yahoo.com>
# License: BSD

from litex.build.generic_platform import *
from litex.build.xilinx import XilinxPlatform, VivadoProgrammer

# IOs ----------------------------------------------------------------------------------------------

_io = [
    ("user_led", 0, Pins("E6"),  IOStandard("LVCMOS33")),

    ("clk50", 0, Pins("N11"), IOStandard("LVCMOS33")),

    ("cpu_reset", 0, Pins("K5"), IOStandard("LVCMOS33")),

    ("serial", 0,
        Subsignal("tx", Pins("M12")),
        Subsignal("rx", Pins("N13")),
        IOStandard("LVCMOS33")
    ),

    ("spi", 0,
        Subsignal("clk",  Pins("N14")),
        Subsignal("cs_n", Pins("N16")),
        Subsignal("mosi", Pins("P15")),
        Subsignal("miso", Pins("P16")),
        IOStandard("LVCMOS33"),
    ),

    ("ddram", 0,
        Subsignal("a", Pins(
            "B14 C8 A14 E12 C9 B10 D9 A12",
            "D8 A13 B12 A9 A8 B11"),
            IOStandard("SSTL135")),
        Subsignal("ba",    Pins("C11 C12 C13"), IOStandard("SSTL135")),
        Subsignal("ras_n", Pins("H13"), IOStandard("SSTL135")),
        Subsignal("cas_n", Pins("G11"), IOStandard("SSTL135")),
        Subsignal("we_n",  Pins("H11"), IOStandard("SSTL135")),
        Subsignal("cs_n",  Pins("F15"), IOStandard("SSTL135")),
        Subsignal("dm", Pins("D13 G15"), IOStandard("SSTL135")),
        Subsignal("dq", Pins(
            "B16 C14 E15 F12 F13 D11 E13 E11",
            "C16 H14 G16 H16 E16 J15 D16 J16"),
            IOStandard("SSTL135")),
        Subsignal("dqs_p", Pins("B15 G14"),
            IOStandard("DIFF_SSTL135")),
        Subsignal("dqs_n", Pins("A15 F14"),
            IOStandard("DIFF_SSTL135")),
        Subsignal("clk_p", Pins("B9"), IOStandard("DIFF_SSTL135")),
        Subsignal("clk_n", Pins("A10"), IOStandard("DIFF_SSTL135")),
        Subsignal("cke",   Pins("G12"), IOStandard("SSTL135")),
        Subsignal("odt",   Pins("H12"), IOStandard("SSTL135")),
        Subsignal("reset_n", Pins("D10"), IOStandard("SSTL135")),
        Misc("SLEW=FAST"),
    ),
]

# Connectors ---------------------------------------------------------------------------------------

_connectors = [
    ("pmoda", "R15 R16 T14 T15 P13 P14 T12 T13"),
    ("pmodb", "R12 R12 N12 K13 P11 P9 R10 R11"),
]

# Platform -----------------------------------------------------------------------------------------

class Platform(XilinxPlatform):
    default_clk_name   = "sys_clk"
    default_clk_period = 1e9/50e6

    def __init__(self):
        XilinxPlatform.__init__(self, "xc7a35tftg256-2", _io, _connectors, toolchain="vivado")
        self.toolchain.bitstream_commands = \
            ["set_property BITSTREAM.CONFIG.SPI_BUSWIDTH 4 [current_design]"]
        self.toolchain.additional_commands = \
            ["write_cfgmem -force -format bin -interface spix4 -size 16 "
             "-loadbit \"up 0x0 {build_name}.bit\" -file {build_name}.bin"]
        self.add_platform_command("set_property INTERNAL_VREF 0.675 [get_iobanks 15]")

    def create_programmer(self):
        return VivadoProgrammer(flash_part="n25q128-3.3v-spi-x1_x2_x4")
