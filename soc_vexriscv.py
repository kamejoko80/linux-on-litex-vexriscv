#!/usr/bin/env python3

import os

from migen import *

from litex.soc.interconnect import wishbone
from litex.soc.integration.soc_core import mem_decoder

from litex.soc.cores.spi_flash import SpiFlash

from periphs.misc import *

# SoCVexRiscv -----------------------------------------------------------------------------------------

def SoCVexRiscv(soc_cls, **kwargs):
    class _SoCLinux(soc_cls):
        soc_cls.csr_map.update({
            "ctrl":       0,
            "uart":       2,
            "timer0":     3,
        })
        soc_cls.interrupt_map.update({
            "uart":       3,
            "timer0":     4,
        })
        soc_cls.mem_map = {
            "rom":          0x00000000,
            "sram":         0x10000000,
            "emulator_ram": 0x20000000,
            "ethmac":       0x30000000,
            "spiflash":     0x50000000,
            "main_ram":     0xc0000000,
            "csr":          0xf0000000,
        }

        def __init__(self, **kwargs):
            soc_cls.__init__(self, cpu_type="vexriscv", cpu_variant="standard", **kwargs)

            # Integrate int module
            self.submodules.gpio_isr = GpioISR(self.platform.request('key', 0), rissing_edge_detect=False)
            self.add_csr("gpio_isr", 10, allow_user_defined=True)
            self.add_interrupt("gpio_isr", 5, allow_user_defined=True)
            
            # Integrate Adder8
            self.submodules.adder8 = Adder8()
            self.add_csr("adder8", 11, allow_user_defined=True)

            # Integrate my uart
            self.platform.add_source(os.path.join("periphs/verilog/uart", "my_uart.v"))
            self.submodules.my_uart = MyUart(self.platform.request("MyUart", 0), self.platform.request("led0", 0))
            self.add_csr("my_uart", 12, allow_user_defined=True)            
            
            # Integrate CAN
            self.platform.add_source(os.path.join("periphs/verilog/can", "can_top.v"))
            self.platform.add_source(os.path.join("periphs/verilog/can", "can_acf.v"))
            self.platform.add_source(os.path.join("periphs/verilog/can", "can_btl.v"))
            self.platform.add_source(os.path.join("periphs/verilog/can", "can_defines.v"))
            self.platform.add_source(os.path.join("periphs/verilog/can", "can_ibo.v"))
            self.platform.add_source(os.path.join("periphs/verilog/can", "can_register_asyn.v"))
            self.platform.add_source(os.path.join("periphs/verilog/can", "can_register_syn.v"))
            self.platform.add_source(os.path.join("periphs/verilog/can", "can_bsp.v"))
            self.platform.add_source(os.path.join("periphs/verilog/can", "can_crc.v"))
            self.platform.add_source(os.path.join("periphs/verilog/can", "can_fifo.v"))
            self.platform.add_source(os.path.join("periphs/verilog/can", "can_register_asyn_syn.v"))
            self.platform.add_source(os.path.join("periphs/verilog/can", "can_registers.v"))
            self.platform.add_source(os.path.join("periphs/verilog/can", "can_register.v"))
            self.submodules.can_controller = CanController()
            
    return _SoCLinux(**kwargs)
