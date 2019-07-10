from migen import *
from migen.fhdl import verilog
from random import randrange

class EdgeDetector(Module):
    def __init__(self):
        self.s = Signal() # Signal input
        self.d = Signal() # Delay signal output
        self.e = Signal() # e = s ^ d
        self.r = Signal() # Rising edge detect
        self.f = Signal() # Falling edge detect

        self.sync += [
            self.d.eq(self.s)
        ]

        self.comb += [
            self.e.eq(self.d ^ self.s),
            self.r.eq(self.e & self.s),
            self.f.eq(self.e & ~self.s),
        ]

def generator(dut):
    for cycle in range(500):
        yield dut.s.eq(randrange(2))
        yield                

if __name__ == "__main__":
    d = EdgeDetector()
    print(verilog.convert(EdgeDetector()))
    # print(verilog.convert(EdgeDetector(), ios = {d.s}))
    # run_simulation(d, generator(d), clocks={"sys": 10}, vcd_name="EdgeDetector.vcd")
