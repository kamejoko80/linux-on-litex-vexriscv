# This file is Copyright (c) 2015 Yann Sionneau <yann.sionneau@gmail.com>
# This file is Copyright (c) 2015-2019 Florent Kermarrec <florent@enjoy-digital.fr>
# License: BSD

from litex.build.generic_platform import *
from litex.build.xilinx import XilinxPlatform, VivadoProgrammer

# IOs ----------------------------------------------------------------------------------------------

_io = [
    ("user_led", 0, Pins("J6"),  IOStandard("LVCMOS33")),
    ("user_led", 1, Pins("H6"),  IOStandard("LVCMOS33")),

    ("sw2", 0, Pins("H7"), IOStandard("LVCMOS33")),

    ("clk50", 0, Pins("M22"), IOStandard("LVCMOS33")),

    ("cpu_reset", 0, Pins("J8"), IOStandard("LVCMOS33")),

    ("serial", 0,
        Subsignal("tx", Pins("E3")),
        Subsignal("rx", Pins("F3")),
        IOStandard("LVCMOS33")
    ),

    ("spiflash4x", 0,
        Subsignal("cs_n", Pins("P18")),
        Subsignal("clk",  Pins("H13")),
        Subsignal("dq",   Pins("R14", "R15", "P14", "N14")),
        IOStandard("LVCMOS33")
    ),

    ("ddram", 0,
        Subsignal("a", Pins(
            "E17 G17 F17 C17 G16 D16 H16 E16",
            "H14 F15 F20 H15 C18 G15"),
            IOStandard("SSTL135")),
        Subsignal("ba",    Pins("B17 D18 A17"), IOStandard("SSTL135")),
        Subsignal("ras_n", Pins("A19"), IOStandard("SSTL135")),
        Subsignal("cas_n", Pins("B19"), IOStandard("SSTL135")),
        Subsignal("we_n",  Pins("A18"), IOStandard("SSTL135")),
        Subsignal("cs_n",  Pins("E22"), IOStandard("SSTL135")),
        Subsignal("dm", Pins("A22 C22"), IOStandard("SSTL135")),
        Subsignal("dq", Pins(
            "D21 C21 B22 B21 D19 E20 C19 D20",
            "C23 D23 B24 B25 C24 C26 A25 B26"),
            IOStandard("SSTL135"),
            Misc("IN_TERM=UNTUNED_SPLIT_40")),
        Subsignal("dqs_p", Pins("B20 A23"),
            IOStandard("DIFF_SSTL135"),
            Misc("IN_TERM=UNTUNED_SPLIT_40")),
        Subsignal("dqs_n", Pins("A20 A24"),
            IOStandard("DIFF_SSTL135"),
            Misc("IN_TERM=UNTUNED_SPLIT_40")),
        Subsignal("clk_p", Pins("F18"), IOStandard("DIFF_SSTL135")),
        Subsignal("clk_n", Pins("F19"), IOStandard("DIFF_SSTL135")),
        Subsignal("cke",   Pins("E18"), IOStandard("SSTL135")),
        Subsignal("odt",   Pins("G19"), IOStandard("SSTL135")),
        Subsignal("reset_n", Pins("H17"), IOStandard("SSTL135")),
        Misc("SLEW=FAST"),
    ),

    ("eth_ref_clk", 0, Pins("U1"), IOStandard("LVCMOS33")),
    ("eth_clocks", 0,
        Subsignal("tx", Pins("M2")),
        Subsignal("rx", Pins("P4")),
        IOStandard("LVCMOS33"),
    ),
    ("eth", 0,
        Subsignal("rst_n",   Pins("R1")),
        Subsignal("mdio",    Pins("H1")),
        Subsignal("mdc",     Pins("H2")),
        Subsignal("rx_dv",   Pins("L3")),
        Subsignal("rx_er",   Pins("U5")),
        Subsignal("rx_data", Pins("M4 N3 N4 P3")),
        Subsignal("tx_en",   Pins("T2")),
        Subsignal("tx_data", Pins("R2 P1 N2 N1")),
        Subsignal("col",     Pins("U4")),
        Subsignal("crs",     Pins("U2")),
        IOStandard("LVCMOS33"),
    ),
]

# Connectors ---------------------------------------------------------------------------------------

_connectors = [
    ("pmoda", "D5 G5 G7 G8 E5 E6 D6 G6"), #J10
    ("pmodb", "H4 F4 A4 A5 J4 G4 B4 B5"), #J11
]

# Platform -----------------------------------------------------------------------------------------

class Platform(XilinxPlatform):
    default_clk_name   = "sys_clk"
    default_clk_period = 1e9/100e6

    def __init__(self):
        XilinxPlatform.__init__(self, "xc7a100tfgg676-2", _io, _connectors, toolchain="vivado")
        self.toolchain.bitstream_commands = \
            ["set_property BITSTREAM.CONFIG.SPI_BUSWIDTH 4 [current_design]"]
        self.toolchain.additional_commands = \
            ["write_cfgmem -force -format bin -interface spix4 -size 16 "
             "-loadbit \"up 0x0 {build_name}.bit\" -file {build_name}.bin"]
        self.add_platform_command("set_property INTERNAL_VREF 0.675 [get_iobanks 16]")
        self.add_platform_command("set_property CLOCK_DEDICATED_ROUTE FALSE [get_nets clk50_IBUF]")

    def create_programmer(self):
        return VivadoProgrammer(flash_part="n25q128-3.3v-spi-x1_x2_x4")
