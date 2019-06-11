import os

from migen import *
from litex.soc.interconnect import wishbone
from litex.soc.integration.soc_core import mem_decoder

from litex.soc.interconnect.csr import *
from litex.soc.interconnect.csr_eventmanager import *

# GPIO interrupt
class GpioISR(Module, AutoCSR):
  def __init__(self, pad, rissing_edge_detect = False):
        # Add int to module
        self.submodules.ev = EventManager()

        if rissing_edge_detect:
            self.ev.gpio_rising_int = EventSourcePulse()
            self.ev.finalize()
            self.comb += self.ev.gpio_rising_int.trigger.eq(pad)
        else:
            self.ev.gpio_falling_int = EventSourceProcess()
            self.ev.finalize()
            self.comb += self.ev.gpio_falling_int.trigger.eq(pad)
 
# Simple Adder8 module
class Adder8(Module, AutoCSR):
  def __init__(self):
        self.op1 = CSRStorage(8)
        self.op2 = CSRStorage(8)
        self.sum = CSRStatus(8)
        self.ena = CSRStorage(1, reset = 0)

        self.sync += [ 
            If(self.ena.storage == 1,
                self.sum.status.eq(self.op1.storage + self.op2.storage),
            )
        ] 
