#!/usr/bin/env python3

import os

from migen import *

from litex.soc.interconnect import wishbone
from litex.soc.integration.soc_core import mem_decoder

from litex.soc.cores.spi_flash import SpiFlashSingle

from liteiclink.serwb.phy import SERWBPHY
from liteiclink.serwb.genphy import SERWBPHY as SERWBLowSpeedPHY
from liteiclink.serwb.core import SERWBCore

# SoCCustom -----------------------------------------------------------------------------------------

def SoCIce40Up(soc_cls, **kwargs):
    class _SoCIce40Up(soc_cls):
        soc_cls.csr_map.update({
            "ctrl":             0,
            "uart":             2,
            "timer0":           3,
            "serwb_master_phy": 20,
            "serwb_slave_phy":  21,
        })
        soc_cls.interrupt_map.update({
            "uart":       3,
            "timer0":     4,
        })
        soc_cls.mem_map = {
            "spiflash":     0x00000000,
            "rom":          0x00020000,
            "sram":         0x10000000,
            "serwb":        0x30000000,
            "csr":          0xf0000000,
        }

        def __init__(self, cpu_variant="lite", uart_baudrate=115200, **kwargs):
            # SoC ----------------------------------------------------------------------------------
            soc_cls.__init__(self,
                cpu_type          = "vexriscv",
                cpu_variant       = cpu_variant,
                uart_baudrate     = uart_baudrate,
                cpu_reset_address = self.mem_map["rom"],
                **kwargs)

            # get platform object
            platform = self.platform
            cpu_reset_address = self.mem_map["spiflash"] + platform.gateware_size

            # SPI flash peripheral
            self.submodules.spiflash = SpiFlashSingle(platform.request("spiflash"),
                                                      dummy=platform.spiflash_read_dummy_bits,
                                                      div=platform.spiflash_clock_div,
                                                      endianness=self.cpu.endianness)
            self.add_constant("SPIFLASH_PAGE_SIZE", platform.spiflash_page_size)
            self.add_constant("SPIFLASH_SECTOR_SIZE", platform.spiflash_sector_size)
            self.add_csr("spiflash")
            self.register_mem("spiflash", self.mem_map["spiflash"], self.spiflash.bus, size=platform.spiflash_total_size)

            bios_size = 0x10000
            self.add_constant("ROM_DISABLE", 1)
            self.add_memory_region("rom", cpu_reset_address, bios_size, type="cached+linker")
            self.flash_boot_address = self.mem_map["spiflash"] + platform.gateware_size + bios_size

            # We don't have a DRAM, so use the remaining SPI flash for user
            # program.
            self.add_memory_region("user_flash",
                self.flash_boot_address,
                # Leave a grace area- possible one-by-off bug in add_memory_region?
                # Possible fix: addr < origin + length - 1
                platform.spiflash_total_size - (self.flash_boot_address - self.mem_map["spiflash"]) - 0x100,
                type="cached+linker")

            # serwb enable
            self.comb += platform.request("serwb_enable").eq(1)

            # serwb master
            self.submodules.serwb_master_phy = SERWBLowSpeedPHY(platform.device, platform.request("serwb_master"), mode="master")

            # serwb slave
            self.submodules.serwb_slave_phy = SERWBLowSpeedPHY(platform.device, platform.request("serwb_slave"), mode="slave")

            # leds
            self.comb += [
                platform.request("user_led", 0).eq(self.serwb_master_phy.init.ready),
                platform.request("user_led", 1).eq(self.serwb_master_phy.init.error),
                platform.request("user_led", 2).eq(self.serwb_slave_phy.init.ready),
                #platform.request("user_led", 3).eq(self.serwb_slave_phy.init.error),
            ]

            # wishbone slave
            serwb_master_core = SERWBCore(self.serwb_master_phy, self.clk_freq, mode="slave")
            self.submodules += serwb_master_core

            # wishbone master
            serwb_slave_core = SERWBCore(self.serwb_slave_phy, self.clk_freq, mode="master")
            self.submodules += serwb_slave_core

            # wishbone test memory
            self.register_mem("serwb", self.mem_map["serwb"], serwb_master_core.etherbone.wishbone.bus, 1024)
            self.submodules.serwb_sram = wishbone.SRAM(1024, init=[i for i in range(1024//4)])
            self.comb += serwb_slave_core.etherbone.wishbone.bus.connect(self.serwb_sram.bus)

        # Boot configuration -----------------------------------------------------------------------
        def configure_boot(self):
            if hasattr(self, "spiflash"):
                self.add_constant("FLASH_BOOT_ADDRESS", self.flash_boot_address)
                self.add_constant("FIRMWARE_IMAGE_FLASH_OFFSET", 0x00A00000)

    return _SoCIce40Up(**kwargs)
