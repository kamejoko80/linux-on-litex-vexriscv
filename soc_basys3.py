#!/usr/bin/env python3

import os

from migen import *

from litex.soc.interconnect import wishbone
from litex.soc.integration.soc_core import mem_decoder

from litex.soc.cores.spi_flash import SpiFlash

from periphs.misc import *
from periphs.accel import *

# SoCAE4GX -----------------------------------------------------------------------------------------

def SoCBASYS3(soc_cls, **kwargs):
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
            "csr":          0xf0000000,
        }

        def __init__(self, **kwargs):
            soc_cls.__init__(self, cpu_type="vexriscv", cpu_variant="lite", **kwargs)

    return _SoCLinux(**kwargs)
