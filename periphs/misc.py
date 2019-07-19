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

# Simple Uart module
class MyUart(Module, AutoCSR):
    def __init__(self, txd, led):
        self.tx_dat = CSRStorage(8)
        self.tx_ena = CSRStorage(1, reset = 0)
        self.tx_bsy = CSRStatus(1)

        tx_status = Signal()

        self.comb += self.tx_bsy.status.eq(tx_status)

        self.specials += [
            Instance("my_uart",
                    i_din=self.tx_dat.storage,
                    i_wr_en=self.tx_ena.storage,
                    i_clk_in=ClockSignal(),
                    o_tx=txd,
                    o_tx_busy=tx_status,
                    )
        ]

    def add_source(self, platform):
            platform.add_source(os.path.join("periphs/verilog/uart", "my_uart.v"))

# Simple wishbone gpio module            
class WbGpio(Module):
    def __init__(self, led):
        self.bus = bus = wishbone.Interface()
        led_wire = Signal(1, reset=1)

        self.comb += led.eq(led_wire)

        # run mw addr 0/1 1 to turn on/off the led
        self.sync += [
            bus.ack.eq(0),
            If(bus.cyc & bus.stb & ~bus.ack,
                bus.ack.eq(1),
                If(bus.we,
                    led_wire.eq(bus.dat_w[0])
                )
            )
        ]

# Wishbone to avalon bridge
class W2ABridge(Module):
    def __init__(self):
        self.bus = bus = wishbone.Interface()

        self.specials += [
            Instance("wb_to_avalon_bridge",
                    # WB IF
                    i_wb_clk_i = ClockSignal(),
                    i_wb_rst_i = ResetSignal(),
                    i_wb_adr_i = bus.adr,
                    i_wb_dat_i = bus.dat_w,
                    i_wb_sel_i = bus.sel,
                    i_wb_we_i  = bus.we,
                    i_wb_cyc_i = bus.cyc,
                    i_wb_stb_i = bus.stb,
                    i_wb_cti_i = bus.cti,
                    i_wb_bte_i = bus.bte,
                    o_wb_dat_o = bus.dat_r,
                    o_wb_ack_o = bus.ack,
                    )
        ]

    def add_source(self, platform):
            platform.add_source(os.path.join("periphs/verilog/w2a", "wb_to_avalon_bridge.v"))

# SJA1000 opencore can controller module
class SJA1000(Module, AutoCSR):
    def __init__(self, canif):    
        # falling edge interrupt
        self.submodules.ev = EventManager()
        self.ev.can_irq = EventSourceProcess()
        self.ev.finalize()

        # can interrupt signal
        can_irq_signal = Signal()

        # wishbone bus
        self.bus = bus = wishbone.Interface()

        self.comb += [
            self.ev.can_irq.trigger.eq(can_irq_signal),
            canif.irq.eq(can_irq_signal) # drives the LED
        ]

        self.specials += [
            Instance("can_top",
                    # WB IF
                    i_wb_clk_i   = ClockSignal(),
                    i_wb_rst_i   = ResetSignal(),
                    i_wb_dat_i   = bus.dat_w,
                    o_wb_dat_o   = bus.dat_r,
                    i_wb_cyc_i   = bus.cyc,
                    i_wb_stb_i   = bus.stb,
                    i_wb_we_i    = bus.we, 
                    i_wb_adr_i   = bus.adr,
                    o_wb_ack_o   = bus.ack,
                    # MISC
                    i_clk_i      = ClockSignal(),
                    i_rx_i       = canif.rx,
                    o_tx_o       = canif.tx,
                    o_bus_off_on = canif.boo,
                    o_irq_on     = can_irq_signal,
                    o_clkout_o   = canif.clkout,
                    )
        ]

    def add_source(self, platform):
            platform.add_source(os.path.join("periphs/verilog/can", "timescale.v"))
            platform.add_source(os.path.join("periphs/verilog/can", "can_defines.v"))
            platform.add_source(os.path.join("periphs/verilog/can", "can_top.v"))
            platform.add_source(os.path.join("periphs/verilog/can", "can_acf.v"))
            platform.add_source(os.path.join("periphs/verilog/can", "can_btl.v"))
            platform.add_source(os.path.join("periphs/verilog/can", "can_ibo.v"))
            platform.add_source(os.path.join("periphs/verilog/can", "can_register_asyn.v"))
            platform.add_source(os.path.join("periphs/verilog/can", "can_register_syn.v"))
            platform.add_source(os.path.join("periphs/verilog/can", "can_bsp.v"))
            platform.add_source(os.path.join("periphs/verilog/can", "can_crc.v"))
            platform.add_source(os.path.join("periphs/verilog/can", "can_fifo.v"))
            platform.add_source(os.path.join("periphs/verilog/can", "can_register_asyn_syn.v"))
            platform.add_source(os.path.join("periphs/verilog/can", "can_registers.v"))
            platform.add_source(os.path.join("periphs/verilog/can", "can_register.v"))

# Opencore SPI master
class SpiMaster(Module, AutoCSR):    
    def __init__(self, pads):
        # rissing edge interrupt
        self.submodules.ev = EventManager()
        self.ev.spi_irq = EventSourcePulse()
        self.ev.finalize()

        # wishbone bus
        self.bus = bus = wishbone.Interface()

        # inverted clk output
        sclk_inv = Signal()

        self.comb += [
           # pads.sclk.eq(~sclk_inv) # Need to invert to test with ADC128S102
           pads.sclk.eq(sclk_inv)
        ]

        self.specials += [
            Instance("spi_top",
                    # WB IF
                    i_wb_clk_i   = ClockSignal(),
                    i_wb_rst_i   = ResetSignal(),
                    i_wb_adr_i   = bus.adr,
                    i_wb_dat_i   = bus.dat_w,
                    i_wb_sel_i   = bus.sel,
                    i_wb_we_i    = bus.we,
                    i_wb_cyc_i   = bus.cyc,
                    i_wb_stb_i   = bus.stb,
                    o_wb_dat_o   = bus.dat_r,
                    o_wb_ack_o   = bus.ack,
                    o_wb_err_o   = bus.err,

                    # SPI signals
                    o_wb_int_o   = self.ev.spi_irq.trigger, # SPI IRQ
                    o_ss_pad_o   = pads.csn,       # SPI chip select need
                    o_sclk_pad_o = sclk_inv,       # SPI clkout
                    o_mosi_pad_o = pads.mosi,      # SPI mosi
                    i_miso_pad_i = pads.miso,      # SPI miso
                    )
        ]

    def add_source(self, platform):
            platform.add_source(os.path.join("periphs/verilog/spi", "spi_defines.v"))
            platform.add_source(os.path.join("periphs/verilog/spi", "spi_clgen.v"))
            platform.add_source(os.path.join("periphs/verilog/spi", "spi_shift.v"))
            platform.add_source(os.path.join("periphs/verilog/spi", "spi_top.v"))
            platform.add_source(os.path.join("periphs/verilog/spi", "timescale.v"))
     