#!/usr/bin/env python3

import argparse
import os
import subprocess

from litex.soc.integration.builder import Builder

from soc_ice40hx import SoCICE40HX
from soc_ice40up import SoCICE40UP
from soc_linux import SoCLinux
from soc_picorv32 import SoCPicorv32
from soc_vexriscv import SoCVexRiscv
from soc_ae4gx import SoCAE4GX
from soc_basys3 import SoCBASYS3
from soc_at7core import SoCAT7CORE

# Board definition----------------------------------------------------------------------------------

class Board:
    def __init__(self, soc_cls, soc_capabilities):
        self.soc_cls = soc_cls
        self.soc_capabilities = soc_capabilities

    def load(self):
        raise NotImplementedError

    def flash(self):
        raise NotImplementedError

# Arty support -------------------------------------------------------------------------------------

class Arty(Board):
    def __init__(self):
        from litex.boards.targets import arty
        Board.__init__(self, arty.EthernetSoC, "serial+ethernet+spiflash")

    def load(self):
        from litex.build.openocd import OpenOCD
        prog = OpenOCD("prog/openocd_xilinx.cfg")
        prog.load_bitstream("build/arty/gateware/top.bit")

    def flash(self):
        flash_regions = {
            "build/arty/gateware/top.bin": "0x00000000", # FPGA image:  loaded at startup
            "buildroot/Image":             "0x00400000", # Linux Image: copied to 0xc0000000 by bios
            "buildroot/rootfs.cpio":       "0x00800000", # File System: copied to 0xc0800000 by bios
            "buildroot/rv32.dtb":          "0x00f00000", # Device tree: copied to 0xc1000000 by bios
            "emulator/emulator.bin":       "0x00f80000", # MM Emulator: copied to 0x20000000 by bios
        }
        from litex.build.openocd import OpenOCD
        prog = OpenOCD("prog/openocd_xilinx.cfg",
            flash_proxy_basename="prog/bscan_spi_xc7a35t.bit")
        prog.set_flash_proxy_dir(".")
        for filename, base in flash_regions.items():
            base = int(base, 16)
            print("Flashing {} at 0x{:08x}".format(filename, base))
            prog.flash(base, filename)

# BASYS3 support -------------------------------------------------------------------------------------

class BASYS3(Board):
    def __init__(self):
        from litex.boards.targets import basys3
        Board.__init__(self, basys3.BaseSoC, "serial")

    def load(self):
        from litex.build.xilinx import VivadoProgrammer
        prog = VivadoProgrammer()
        prog.load_bitstream("build/basys3/gateware/top.bit")

    def flash_gw(self):
        from litex.build.openocd import OpenOCD
        prog = OpenOCD("prog/openocd_xilinx.cfg",
            flash_proxy_basename="prog/bscan_spi_xc7a35t.bit")
        prog.set_flash_proxy_dir(".")
        prog.flash(0, "build/basys3/gateware/top.bin")

# AT7CORE support -------------------------------------------------------------------------------------

class AT7CORE(Board):
    def __init__(self):
        from litex.boards.targets import at7core
        Board.__init__(self, at7core.BaseSoC, "serial")

    def load(self):
        from litex.build.xilinx import VivadoProgrammer
        prog = VivadoProgrammer()
        prog.load_bitstream("build/at7core/gateware/top.bit")

    def flash_gw(self):
        from litex.build.openocd import OpenOCD
        prog = OpenOCD("prog/openocd_xilinx.cfg",
            flash_proxy_basename="prog/bscan_spi_xc7a100t.bit")
        prog.set_flash_proxy_dir(".")
        prog.flash(0, "build/at7core/gateware/top.bin")

# NeTV2 support ------------------------------------------------------------------------------------

class NeTV2(Board):
    def __init__(self):
        from litex.boards.targets import netv2
        Board.__init__(self, netv2.EthernetSoC, "serial+ethernet")

    def load(self):
        from litex.build.xilinx import VivadoProgrammer
        prog = VivadoProgrammer()
        prog.load_bitstream("build/netv2/gateware/top.bit")

# Genesys2 support ---------------------------------------------------------------------------------

class Genesys2(Board):
    def __init__(self):
        from litex.boards.targets import genesys2
        Board.__init__(self, genesys2.BaseSoC, "serial")

    def load(self):
        from litex.build.xilinx import VivadoProgrammer
        prog = VivadoProgrammer()
        prog.load_bitstream("build/genesys2/gateware/top.bit")

# KCU105 support -----------------------------------------------------------------------------------

class KCU105(Board):
    def __init__(self):
        from litex.boards.targets import kcu105
        Board.__init__(self, kcu105.EthernetSoC, "serial+ethernet")

    def load(self):
        from litex.build.xilinx import VivadoProgrammer
        prog = VivadoProgrammer()
        prog.load_bitstream("build/kcu105/gateware/top.bit")


# Nexys4DDR support --------------------------------------------------------------------------------

class Nexys4DDR(Board):
    def __init__(self):
        from litex.boards.targets import nexys4ddr
        Board.__init__(self, nexys4ddr.EthernetSoC, "serial+ethernet")

    def load(self):
        from litex.build.xilinx import VivadoProgrammer
        prog = VivadoProgrammer()
        prog.load_bitstream("build/nexys4ddr/gateware/top.bit")

# NexysVideo support --------------------------------------------------------------------------------

class NexysVideo(Board):
    def __init__(self):
        from litex.boards.targets import nexys_video
        Board.__init__(self, nexys_video.EthernetSoC, "serial")

    def load(self):
        from litex.build.xilinx import VivadoProgrammer
        prog = VivadoProgrammer(vivado_path=vivado_path)
        prog.load_bitstream("build/nexys_video/gateware/top.bit")

# MiniSpartan6 support -----------------------------------------------------------------------------

class MiniSpartan6(Board):
    def __init__(self):
        from litex.boards.targets import minispartan6
        Board.__init__(self, minispartan6.BaseSoC, "serial")

    def load(self):
        os.system("xc3sprog -c ftdi build/minispartan6/gateware/top.bit")


# Versa ECP5 support -------------------------------------------------------------------------------

class VersaECP5(Board):
    def __init__(self):
        from litex.boards.targets import versa_ecp5
        Board.__init__(self, versa_ecp5.EthernetSoC, "serial+ethernet")

    def load(self):
        os.system("openocd -f prog/ecp5-versa5g.cfg -c \"transport select jtag; init; svf build/versa_ecp5/gateware/top.svf; exit\"")

# ULX3S support ------------------------------------------------------------------------------------

class ULX3S(Board):
    def __init__(self):
        from litex.boards.targets import ulx3s
        Board.__init__(self, ulx3s.BaseSoC, "serial")

    def load(self):
        os.system("ujprog build/ulx3s/gateware/top.svf")

# ICE40 HX8K support ------------------------------------------------------------------------------------

class ICE40_HX8K_B_EVN(Board):
    def __init__(self):
        from litex.boards.targets import ice40_hx8k_b_evn
        Board.__init__(self, ice40_hx8k_b_evn.BaseSoC, "serial")

    def flash_gw(self):
        print("Flash gateware image")
        subprocess.call(["iceprog", "-o", "0", "build/ice40_hx8k_b_evn/gateware/top.bin"])

    def flash_bios(self):
        print("Flash bios image")
        subprocess.call(["iceprog", "-o", "0x30000", "build/ice40_hx8k_b_evn/software/bios/bios.bin"])

    def flash_fw(self):
        print("Flash frimware image")
        subprocess.call(["iceprog", "-o", "0x40000", "build/ice40_hx8k_b_evn/software/firmware/firmware.bin"])


# ICE40 UP5K support ------------------------------------------------------------------------------------

class ICE40_UP5K_B_EVN(Board):
    def __init__(self):
        from litex.boards.targets import ice40_up5k_b_evn
        Board.__init__(self, ice40_up5k_b_evn.BaseSoC, "serial")

    def flash_gw(self):
        print("Flash gateware image")
        subprocess.call(["iceprog", "-o", "0", "build/ice40_up5k_b_evn/gateware/top.bin"])

    def flash_bios(self):
        print("Flash bios image")
        subprocess.call(["iceprog", "-o", "0x20000", "build/ice40_up5k_b_evn/software/bios/bios.bin"])

    def flash_fw(self):
        print("Flash frimware image")
        subprocess.call(["iceprog", "-o", "0x30000", "build/ice40_hx8k_b_evn/software/firmware/firmware.bin"])

# De0Nano support ------------------------------------------------------------------------------------

class De0Nano(Board):
    def __init__(self):
        from litex.boards.targets import de0nano
        Board.__init__(self, de0nano.BaseSoC, "serial")

    def load(self):
        from litex.build.altera import USBBlaster
        prog = USBBlaster()
        prog.load_bitstream("build/de0nano/gateware/top.sof")

# QmaTech support ------------------------------------------------------------------------------------

class QmaTech(Board):
    def __init__(self):
        from litex.boards.targets import qmatech
        Board.__init__(self, qmatech.BaseSoC, "serial")

    def load(self):
        from litex.build.altera import USBBlaster
        prog = USBBlaster()
        prog.load_bitstream("build/qmatech/gateware/top.sof")

# AE4GX support ------------------------------------------------------------------------------------

class AE4GX(Board):
    def __init__(self):
        from litex.boards.targets import ae4gx
        Board.__init__(self, ae4gx.BaseSoC, "serial")

    def load(self):
        from litex.build.altera import USBBlaster
        prog = USBBlaster()
        prog.load_bitstream("build/ae4gx/gateware/top.sof")

# Main ---------------------------------------------------------------------------------------------

supported_boards = {
    # Xilinx
    "arty":         Arty,
    "basys3":       BASYS3,
    "at7core":      AT7CORE,
    "netv2":        NeTV2,
    "genesys2":     Genesys2,
    "kcu105":       KCU105,
    "nexys4ddr":    Nexys4DDR,
    "nexys_video":  NexysVideo,
    "minispartan6": MiniSpartan6,
    # Lattice
    "versa_ecp5":   VersaECP5,
    "ulx3s":        ULX3S,
    "ice40_hx8k_b_evn": ICE40_HX8K_B_EVN,
    "ice40_up5k_b_evn": ICE40_UP5K_B_EVN,
    # Altera/Intel
    "de0nano":      De0Nano,
    # QMA/Tech
    "qmatech":      QmaTech,
    # AE4GX
    "ae4gx":        AE4GX,
}

def main():
    description = "Linux on LiteX-VexRiscv\n\n"
    description += "Available boards:\n"
    for name in supported_boards.keys():
        description += "- " + name + "\n"
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--board", required=True, help="FPGA board")
    parser.add_argument("--build", action="store_true", help="build bitstream")
    parser.add_argument("--build_sw", action="store_true", help="build software only")
    parser.add_argument("--load", action="store_true", help="load bitstream (to SRAM)")
    parser.add_argument("--flash", action="store_true", help="flash bitstream/images (to SPI Flash)")
    parser.add_argument("--flash_gw", action="store_true", help="flash bitstream/images (to SPI Flash)")
    parser.add_argument("--flash_bios", action="store_true", help="flash bios (to SPI Flash)")
    parser.add_argument("--flash_fw", action="store_true", help="flash firmware (to SPI Flash)")
    parser.add_argument("--local-ip", default="192.168.1.50", help="local IP address")
    parser.add_argument("--remote-ip", default="192.168.1.100", help="remote IP address of TFTP server")
    args = parser.parse_args()

    if args.board == "all":
        board_names = list(supported_boards.keys())
    else:
        board_names = [args.board]
    for board_name in board_names:
        board = supported_boards[board_name]()
        soc_kwargs = {}
        if board_name in ["versa_ecp5", "ulx3s"]:
            soc_kwargs["toolchain"] = "trellis"
        if board_name in ["qmatech"]:
            soc = SoCVexRiscv(board.soc_cls, **soc_kwargs)
        elif board_name in ["ae4gx"]:
            soc = SoCAE4GX(board.soc_cls, **soc_kwargs)
        elif board_name in ["basys3"]:
            soc = SoCBASYS3(board.soc_cls, **soc_kwargs)
        elif board_name in ["at7core"]:
            soc = SoCAT7CORE(board.soc_cls, **soc_kwargs)
        elif board_name in ["ice40_hx8k_b_evn"]:
            soc = SoCICE40HX(board.soc_cls, **soc_kwargs)
        elif board_name in ["ice40_up5k_b_evn"]:
            soc = SoCICE40UP(board.soc_cls, **soc_kwargs)
        else:
            soc = SoCLinux(board.soc_cls, **soc_kwargs)

        if args.build:
            builder = Builder(soc, output_dir="build/" + board_name)
            builder.add_software_package(name="firmware")
            builder.build()

        if args.build_sw:
            builder = Builder(soc, output_dir="build/" + board_name, compile_gateware=False)
            builder.add_software_package(name="firmware")
            builder.build()

        if args.load:
            board.load()

        if args.flash:
            board.flash_gw()
            board.flash_bios()
            board.flash_fw()

        if args.flash_gw:
            board.flash_gw()

        if args.flash_bios:
            board.flash_bios()

        if args.flash_fw:
            board.flash_fw()

if __name__ == "__main__":
    main()
