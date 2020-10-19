#!/usr/bin/env python3

# This file is Copyright (c) 2020 Phuong Dang <kamejokoxx@yahoo.com>
# License: BSD

import os
import sys

from migen import *
from litex.build.generic_platform import *
from litex.build.sim import SimPlatform
from litex.build.sim.config import SimConfig
from migen.genlib.io import CRG
from migen.genlib.misc import timeline
from migen.genlib.fifo import SyncFIFOBuffered
from migen.genlib.misc import WaitTimer
from migen.fhdl.specials import Tristate

from litex.soc.interconnect import wishbone
from litex.soc.integration.soc_core import mem_decoder

from litex.soc.interconnect.csr import *
from litex.soc.interconnect.csr_eventmanager import *

# IOs ----------------------------------------------------------------------

_io = [
    ("sys_clk", 0, Pins(1)),
    ("sys_rst", 0, Pins(1)),
    ("serial", 0,
        Subsignal("source_valid", Pins()),
        Subsignal("source_ready", Pins()),
        Subsignal("source_data", Pins(8)),

        Subsignal("sink_valid", Pins()),
        Subsignal("sink_ready", Pins()),
        Subsignal("sink_data", Pins(8)),
    ),
    ("spi_array", 0,

        # sck array
        Subsignal("sck_0", Pins(1)),
        Subsignal("sck_1", Pins(1)),
        Subsignal("sck_2", Pins(1)),
        Subsignal("sck_3", Pins(1)),
        Subsignal("sck_4", Pins(1)),
        Subsignal("sck_5", Pins(1)),
        Subsignal("sck_6", Pins(1)),
        Subsignal("sck_7", Pins(1)),

        # mosi array
        Subsignal("mosi_0", Pins(1)),
        Subsignal("mosi_1", Pins(1)),
        Subsignal("mosi_2", Pins(1)),
        Subsignal("mosi_3", Pins(1)),
        Subsignal("mosi_4", Pins(1)),
        Subsignal("mosi_5", Pins(1)),
        Subsignal("mosi_6", Pins(1)),
        Subsignal("mosi_7", Pins(1)),

        # miso array
        Subsignal("miso_0", Pins(1)),
        Subsignal("miso_1", Pins(1)),
        Subsignal("miso_2", Pins(1)),
        Subsignal("miso_3", Pins(1)),
        Subsignal("miso_4", Pins(1)),
        Subsignal("miso_5", Pins(1)),
        Subsignal("miso_6", Pins(1)),
        Subsignal("miso_7", Pins(1)),

        # csn array
        Subsignal("csn_0", Pins(1)),
        Subsignal("csn_1", Pins(1)),
        Subsignal("csn_2", Pins(1)),
        Subsignal("csn_3", Pins(1)),
        Subsignal("csn_4", Pins(1)),
        Subsignal("csn_5", Pins(1)),
        Subsignal("csn_6", Pins(1)),
        Subsignal("csn_7", Pins(1)),

        # irq pin
        Subsignal("irq", Pins(1)),
    ),
]

# Platform -----------------------------------------------------------------

class Platform(SimPlatform):
    def __init__(self):
        SimPlatform.__init__(self, "SIM", _io)

class EdgeDetector(Module):
    def __init__(self):
        self.i   = Signal() # Signal input
        self.r   = Signal() # Rising edge detect
        self.f   = Signal() # Falling edge detect
        self.cnt = Signal(2)

        self.comb += [
            self.r.eq(self.cnt == 1),
            self.f.eq(self.cnt == 2),
        ]

        self.sync += [
            self.cnt[1].eq(self.cnt[0]),
            self.cnt[0].eq(self.i),
        ]

class SPIArrayMaster(Module, AutoCSR):
    def __init__(self, freq, baudrate, pads):
        # CSR interface
        # IE   : Interrupt enable (0: disable, 1: enable)
        # IPOL : IRQ pin polaration (0: falling edge, 1: rising edge)
        # CPHA : Clock phase
        # CPOL : Clock polar
        self.config    = CSRStorage(4, reset=0x00) # [IE, IPOL, CPHA, CPOL]
        self.tx_data   = CSRStorage(8)
        self.done      = CSRStatus(reset=1)
        self.start     = CSR()

        # SPI internal signals
        self.csn       = CSRStorage(8, reset=0xFF)
        self.sck       = Signal()
        self.mosi      = Signal()
        self.miso_0    = Signal()     # miso line 0
        self.miso_1    = Signal()     # miso line 1
        self.miso_2    = Signal()     # miso line 2
        self.miso_3    = Signal()     # miso line 3
        self.miso_4    = Signal()     # miso line 4
        self.miso_5    = Signal()     # miso line 5
        self.miso_6    = Signal()     # miso line 6
        self.miso_7    = Signal()     # miso line 7

        # Check if we need more miso line
        self.rx_data_0 = CSRStatus(8) # miso line 0
        self.rx_data_1 = CSRStatus(8) # miso line 1
        self.rx_data_2 = CSRStatus(8) # miso line 2
        self.rx_data_3 = CSRStatus(8) # miso line 3
        self.rx_data_4 = CSRStatus(8) # miso line 4
        self.rx_data_5 = CSRStatus(8) # miso line 5
        self.rx_data_6 = CSRStatus(8) # miso line 6
        self.rx_data_7 = CSRStatus(8) # miso line 7

        # Internal signals
        self.prescaler = Signal(max=int(freq/(2*baudrate)))
        self.frame     = Signal(reset=1)
        self.spi_clk   = Signal()
        self.tx_buf    = Signal(8)
        self.rx_buf    = Array(Signal(8) for a in range(8))
        self.edge_cnt  = Signal(5)
        self.irq       = Signal()
        self.irq_pad   = Signal()

        # SPI clock generation
        self.sync += [
            If(~self.frame,
                If(self.prescaler == (int(freq/(2*baudrate)) - 1),
                    self.prescaler.eq(0),
                    self.edge_cnt.eq(self.edge_cnt + 1),
                    If(self.edge_cnt < 16,
                        self.spi_clk.eq(~self.spi_clk)
                    ).Else(
                        self.frame.eq(1),
                        self.rx_data_0.status.eq(self.rx_buf[0]), # miso line 0
                        self.rx_data_1.status.eq(self.rx_buf[1]), # miso line 1
                        self.rx_data_2.status.eq(self.rx_buf[2]), # miso line 2
                        self.rx_data_3.status.eq(self.rx_buf[3]), # miso line 3
                        self.rx_data_4.status.eq(self.rx_buf[4]), # miso line 4
                        self.rx_data_5.status.eq(self.rx_buf[5]), # miso line 5
                        self.rx_data_6.status.eq(self.rx_buf[6]), # miso line 6
                        self.rx_data_7.status.eq(self.rx_buf[7]), # miso line 7
                        self.done.status.eq(1),
                        self.irq.eq(1)
                    )
                ).Else(
                    self.prescaler.eq(self.prescaler + 1)
                )
            )
        ]

        ####### pin signal assignment #######

        self.comb += [
            # signal sck
            If(self.config.storage[0] == 0, # CPOL = 0
                self.sck.eq(self.spi_clk)
            ).Else(
                self.sck.eq(~self.spi_clk)
            ),
            # signal mosi
            self.mosi.eq(self.tx_buf[7]),
            # pin irq
            If(self.config.storage[3],     # IE   = 1 (Interrupt enable)
                If(self.config.storage[2], # IPOL = 1 (Active high)
                    self.irq_pad.eq(self.irq)
                ).Else(
                   self.irq_pad.eq(~self.irq)
                )
            ).Else(
                self.irq_pad.eq(0) # Should be configured as Hi-Z
            )
        ]

        # pin irq
        if hasattr(pads, "irq"):
            self.comb += pads.irq.eq(self.irq_pad)   # irq pad

        # pin sck_x
        if hasattr(pads, "sck_0"):
            self.comb += pads.sck_0.eq(self.sck)     # sck line 0
        if hasattr(pads, "sck_1"):
            self.comb += pads.sck_1.eq(self.sck)     # sck line 1
        if hasattr(pads, "sck_2"):
            self.comb += pads.sck_2.eq(self.sck)     # sck line 2
        if hasattr(pads, "sck_3"):
            self.comb += pads.sck_3.eq(self.sck)     # sck line 3
        if hasattr(pads, "sck_4"):
            self.comb += pads.sck_4.eq(self.sck)     # sck line 4
        if hasattr(pads, "sck_5"):
            self.comb += pads.sck_5.eq(self.sck)     # sck line 5
        if hasattr(pads, "sck_6"):
            self.comb += pads.sck_6.eq(self.sck)     # sck line 6
        if hasattr(pads, "sck_7"):
            self.comb += pads.sck_7.eq(self.sck)     # sck line 7

        # pin miso_x
        if hasattr(pads, "miso_0"):
            self.comb += self.miso_0.eq(pads.miso_0) # miso line 0
        if hasattr(pads, "miso_1"):
            self.comb += self.miso_1.eq(pads.miso_1) # miso line 1
        if hasattr(pads, "miso_2"):
            self.comb += self.miso_2.eq(pads.miso_2) # miso line 2
        if hasattr(pads, "miso_3"):
            self.comb += self.miso_3.eq(pads.miso_3) # miso line 3
        if hasattr(pads, "miso_4"):
            self.comb += self.miso_4.eq(pads.miso_4) # miso line 4
        if hasattr(pads, "miso_5"):
            self.comb += self.miso_5.eq(pads.miso_5) # miso line 5
        if hasattr(pads, "miso_6"):
            self.comb += self.miso_6.eq(pads.miso_6) # miso line 6
        if hasattr(pads, "miso_7"):
            self.comb += self.miso_7.eq(pads.miso_7) # miso line 7

        # pin mosi_x
        if hasattr(pads, "mosi_0"):
            self.comb += pads.mosi_0.eq(self.mosi)   # miso line 0
        if hasattr(pads, "mosi_1"):
            self.comb += pads.mosi_1.eq(self.mosi)   # miso line 1
        if hasattr(pads, "mosi_2"):
            self.comb += pads.mosi_2.eq(self.mosi)   # miso line 2
        if hasattr(pads, "mosi_3"):
            self.comb += pads.mosi_3.eq(self.mosi)   # miso line 3
        if hasattr(pads, "mosi_4"):
            self.comb += pads.mosi_4.eq(self.mosi)   # miso line 4
        if hasattr(pads, "mosi_5"):
            self.comb += pads.mosi_5.eq(self.mosi)   # miso line 5
        if hasattr(pads, "mosi_6"):
            self.comb += pads.mosi_6.eq(self.mosi)   # miso line 6
        if hasattr(pads, "mosi_7"):
            self.comb += pads.mosi_7.eq(self.mosi)   # miso line 7

        # pin csn_x
        if hasattr(pads, "csn_0"):
            self.comb += pads.csn_0.eq(self.csn.storage[0]) # csn line 0
        if hasattr(pads, "csn_1"):
            self.comb += pads.csn_1.eq(self.csn.storage[1]) # csn line 1
        if hasattr(pads, "csn_2"):
            self.comb += pads.csn_2.eq(self.csn.storage[2]) # csn line 2
        if hasattr(pads, "csn_3"):
            self.comb += pads.csn_3.eq(self.csn.storage[3]) # csn line 3
        if hasattr(pads, "csn_4"):
            self.comb += pads.csn_4.eq(self.csn.storage[4]) # csn line 4
        if hasattr(pads, "csn_5"):
            self.comb += pads.csn_5.eq(self.csn.storage[5]) # csn line 5
        if hasattr(pads, "csn_6"):
            self.comb += pads.csn_6.eq(self.csn.storage[6]) # csn line 6
        if hasattr(pads, "csn_7"):
            self.comb += pads.csn_7.eq(self.csn.storage[7]) # csn line 7

        # SPI start condition
        self.sync += [
            If(self.start.re & self.start.r & self.done.status,
                self.tx_buf.eq(self.tx_data.storage),
                self.rx_buf[0].eq(0), # miso line 0
                self.rx_buf[1].eq(0), # miso line 1
                self.rx_buf[2].eq(0), # miso line 2
                self.rx_buf[3].eq(0), # miso line 3
                self.rx_buf[4].eq(0), # miso line 4
                self.rx_buf[5].eq(0), # miso line 5
                self.rx_buf[6].eq(0), # miso line 6
                self.rx_buf[7].eq(0), # miso line 7
                self.prescaler.eq(0),
                self.frame.eq(0),
                self.done.status.eq(0),
                self.edge_cnt.eq(0),
                self.irq.eq(0),
            )
        ]

        # Generate rising/falling edge output
        edt = ResetInserter()(EdgeDetector())
        self.submodules += edt

        self.comb += [
            edt.reset.eq(self.frame),
            edt.i.eq(self.spi_clk),
        ]

        # Submodule FSM handles data in/out activities
        fsm = FSM(reset_state = "IDLE")
        self.submodules += fsm

        # FSM behavior description
        fsm.act("IDLE",
            If(~self.frame,
                If(self.config.storage[1],  # CPHA = 1
                    If(edt.r,
                        NextState("SHIFT"),
                    )
                ).Else(
                    NextState("SHIFT"),
                )
            ).Else(
                NextState("IDLE"),
            )
        )
        fsm.act("SHIFT",
            If(self.frame,
                NextState("IDLE")
            ).Else(
                If(self.config.storage[1], # CPHA = 1
                    If(edt.r,
                        NextValue(self.tx_buf, self.tx_buf << 1),
                        NextValue(self.rx_buf[0][0], self.miso_0),      # miso line 0
                        NextValue(self.rx_buf[1][0], self.miso_1),      # miso line 1
                        NextValue(self.rx_buf[2][0], self.miso_2),      # miso line 2
                        NextValue(self.rx_buf[3][0], self.miso_3),      # miso line 3
                        NextValue(self.rx_buf[4][0], self.miso_4),      # miso line 4
                        NextValue(self.rx_buf[5][0], self.miso_5),      # miso line 5
                        NextValue(self.rx_buf[6][0], self.miso_6),      # miso line 6
                        NextValue(self.rx_buf[7][0], self.miso_7),      # miso line 7
                        NextState("SHIFT")
                    ),
                    If(edt.f,
                        NextValue(self.rx_buf[0], self.rx_buf[0] << 1), # miso line 0
                        NextValue(self.rx_buf[1], self.rx_buf[1] << 1), # miso line 1
                        NextValue(self.rx_buf[2], self.rx_buf[2] << 1), # miso line 2
                        NextValue(self.rx_buf[3], self.rx_buf[3] << 1), # miso line 3
                        NextValue(self.rx_buf[4], self.rx_buf[4] << 1), # miso line 4
                        NextValue(self.rx_buf[5], self.rx_buf[5] << 1), # miso line 5
                        NextValue(self.rx_buf[6], self.rx_buf[6] << 1), # miso line 6
                        NextValue(self.rx_buf[7], self.rx_buf[7] << 1), # miso line 7
                    )
                ).Else( # CPHA = 0
                    If(edt.f,
                        NextValue(self.tx_buf, self.tx_buf << 1),
                        NextValue(self.rx_buf[0][0], self.miso_0),      # miso line 0
                        NextValue(self.rx_buf[1][0], self.miso_1),      # miso line 1
                        NextValue(self.rx_buf[2][0], self.miso_2),      # miso line 2
                        NextValue(self.rx_buf[3][0], self.miso_3),      # miso line 3
                        NextValue(self.rx_buf[4][0], self.miso_4),      # miso line 4
                        NextValue(self.rx_buf[5][0], self.miso_5),      # miso line 5
                        NextValue(self.rx_buf[6][0], self.miso_6),      # miso line 6
                        NextValue(self.rx_buf[7][0], self.miso_7),      # miso line 7
                        NextState("SHIFT")
                    ),
                    If(edt.r,
                        NextValue(self.rx_buf[0], self.rx_buf[0] << 1), # miso line 0
                        NextValue(self.rx_buf[1], self.rx_buf[1] << 1), # miso line 1
                        NextValue(self.rx_buf[2], self.rx_buf[2] << 1), # miso line 2
                        NextValue(self.rx_buf[3], self.rx_buf[3] << 1), # miso line 3
                        NextValue(self.rx_buf[4], self.rx_buf[4] << 1), # miso line 4
                        NextValue(self.rx_buf[5], self.rx_buf[5] << 1), # miso line 5
                        NextValue(self.rx_buf[6], self.rx_buf[6] << 1), # miso line 6
                        NextValue(self.rx_buf[7], self.rx_buf[7] << 1), # miso line 7
                    )
                )
            )
        )

######################### Test bench functions #######################################

def SPIArrayMasterTestBench(dut):

    for cycle in range(5000):

        if cycle == 1:
            yield dut.config.storage.eq(0x0C)

        if cycle == 2:
            yield dut.tx_data.storage.eq(0xA5)
            yield dut.start.re.eq(1)
            yield dut.start.r.eq(1)

        if cycle == 3:
            yield dut.start.re.eq(0)
            yield dut.start.r.eq(0)

        if cycle == 1000:
            yield dut.tx_data.storage.eq(0x24)
            yield dut.start.re.eq(1)
            yield dut.start.r.eq(1)

        if cycle == 1001:
            yield dut.start.re.eq(0)
            yield dut.start.r.eq(0)

        yield

if __name__ == "__main__":
    platform = Platform()
    spi_pads = platform.request("spi_array")
    dut = SPIArrayMaster(freq=50000000, baudrate=1000000, pads=spi_pads)
    print(verilog.convert(SPIArrayMaster(freq=50000000, baudrate=1000000, pads=spi_pads)))
    run_simulation(dut, SPIArrayMasterTestBench(dut), clocks={"sys": 10}, vcd_name="SPIArrayMaster.vcd")