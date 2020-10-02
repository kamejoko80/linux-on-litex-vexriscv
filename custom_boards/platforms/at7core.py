# This file is Copyright (c) 2020 Phuong Dang <phuongminh.xxxx@gmail.com>
# License: BSD

from litex.build.generic_platform import *
from litex.build.xilinx import XilinxPlatform, VivadoProgrammer

# IOs ----------------------------------------------------------------------------------------------

_io = [
    ("user_led", 0, Pins("B19"),  IOStandard("LVCMOS33")),
    ("user_led", 1, Pins("A19"),  IOStandard("LVCMOS33")),

    ("sw2", 0, Pins("B20"), IOStandard("LVCMOS33")),
    ("sw3", 0, Pins("A20"), IOStandard("LVCMOS33")),

    ("clk50", 0, Pins("D18"), IOStandard("LVCMOS33")),

    ("cpu_reset", 0, Pins("A20"), IOStandard("LVCMOS33")), # SW3

    ("serial", 0,
        Subsignal("tx", Pins("A5")), # U2 07
        Subsignal("rx", Pins("B5")), # U2 08
        IOStandard("LVCMOS33")
    ),

    ("spi", 0,
        Subsignal("clk",  Pins("A4")), # U2 09
        Subsignal("cs_n", Pins("B4")), # U2 10
        Subsignal("mosi", Pins("A2")), # U2 11
        Subsignal("miso", Pins("A3")), # U2 12
        IOStandard("LVCMOS33"),
    ),

    ("spiflash4x", 0,
        Subsignal("cs_n", Pins("P18")),
        Subsignal("dq",   Pins("R14", "R15", "P14", "N14")),
        IOStandard("LVCMOS33")
    ),  
    
    ("serwb_master", 0,
        Subsignal("clk",  Pins("A22")), # U4 07
        Subsignal("tx",   Pins("A23")), # U4 09
        Subsignal("rx",   Pins("A25")), # U4 11
        IOStandard("LVCMOS33"),
    ),

    ("serwb_slave", 0,
        Subsignal("clk",  Pins("B22")), # U4 08
        Subsignal("tx",   Pins("B25")), # U4 12
        Subsignal("rx",   Pins("A24")), # U4 10
        IOStandard("LVCMOS33"),
    ),

    ("serwb_enable", 0, Pins("C23"), IOStandard("LVCMOS33")), # U4 13
]

# Connectors ---------------------------------------------------------------------------------------

_connectors = [
    ("pmoda", "U25 T25 W26 Y26 W24 AA25 AB25 AC26"), # U4
    ("pmodb", "U26 T24 V26 W25 V24 Y25 AA24 AB26"),  # U4
]

# Platform -----------------------------------------------------------------------------------------

class Platform(XilinxPlatform):
    default_clk_name   = "sys_clk"
    default_clk_period = 1e9/50e6

    def __init__(self):
        XilinxPlatform.__init__(self, "xc7a100tfgg676-2", _io, _connectors, toolchain="vivado")
        self.toolchain.bitstream_commands = \
            ["set_property BITSTREAM.CONFIG.SPI_BUSWIDTH 4 [current_design]"]
        self.toolchain.additional_commands = \
            ["write_cfgmem -force -format bin -interface spix4 -size 16 "
             "-loadbit \"up 0x0 {build_name}.bit\" -file {build_name}.bin"]
        # self.add_platform_command("set_property INTERNAL_VREF 0.675 [get_iobanks 16]")
        # self.add_platform_command("set_property CLOCK_DEDICATED_ROUTE FALSE [get_nets clk50_IBUF]")

    def create_programmer(self):
        return VivadoProgrammer(flash_part="n25q128-3.3v-spi-x1_x2_x4")
