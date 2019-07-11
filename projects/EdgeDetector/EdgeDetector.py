import os

from migen import *
from migen.fhdl import verilog
from migen.genlib.misc import WaitTimer
from random import randrange

class Debouncer(Module):
    def __init__(self, cycles=1):
        self.i = Signal()
        self.o = Signal()

        timer = WaitTimer(cycles - 1)
        self.submodules += timer
        new = Signal()
        rst = Signal(reset=1)
        self.sync += [
            If(timer.wait,
                If(timer.done,
                    timer.wait.eq(0),
                    new.eq(~new),
                ),
            ).Elif(self.i == new,
                timer.wait.eq(1),
            ),
            If(rst,
                rst.eq(0),
                timer.wait.eq(0),
                new.eq(~self.i),
            ),
        ]
        self.comb += [
            self.o.eq(Mux(timer.wait, new, self.i)),
        ]

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

class ShifterIn(Module):
    def __init__(self):
        self.sck     = Signal()
        self.si      = Signal()
        self.start   = Signal()
        self.rising  = Signal()
        self.falling = Signal()
        self.done    = Signal()
        self.dout    = Signal(8)
        self.cnt     = Signal(4)

        fsm = FSM(reset_state = "IDLE")
        edt = EdgeDetector()

        self.submodules += fsm #, edt

        #self.comb += [
        #    edt.s.eq(self.sck),     # Signal input
        #    self.rising.eq(edt.r),  # Rising edege detecting input
        #    self.falling.eq(edt.f), # Falling edge detecting output
        #]

        fsm.act("IDLE",
            If(self.start == 1,
                NextValue(self.cnt, 0x00),
                NextState("SHIFTING"),
            )
        )
        fsm.act("SHIFTING",
            If(self.cnt == 8,
                NextValue(self.done, 1),
                NextState("IDLE"),
            ),
            If(self.rising,
                If(self.cnt < 8,
                    NextValue(self.cnt, self.cnt + 1),
                    If(self.si,
                        NextValue(self.dout[0], 1),
                    ).Else(
                        NextValue(self.dout[0], 0),
                    )                    
                )
            ),
            If(self.falling,
                If(self.cnt < 8,
                    NextValue(self.dout, self.dout << 1)
                )
            )
        )

        self.sync += [
            If(self.rising, self.start.eq(0)),
            If(self.falling, self.done.eq(0))
        ]

class ShifterOut(Module):
    def __init__(self):
        self.sck     = Signal()
        self.so      = Signal()
        self.start   = Signal()
        self.rising  = Signal()
        self.falling = Signal()
        self.done    = Signal()
        self.din     = Signal(8)
        self.cnt     = Signal(4)

        fsm = FSM(reset_state = "IDLE")
        edt = EdgeDetector()

        self.submodules += fsm #, edt

        #self.comb += [
        #    edt.s.eq(self.sck),     # Signal input
        #    self.rising.eq(edt.r),  # Rising edege detecting input
        #    self.falling.eq(edt.f), # Falling edge detecting output
        #]

        fsm.act("IDLE",
            If(self.start == 1,
                NextValue(self.cnt, 0x00),
                NextState("SHIFTING"),
            )
        )
        fsm.act("SHIFTING",
            If(self.cnt == 8,
                NextValue(self.done, 1),
                NextValue(self.so, 0),
                NextState("IDLE"),
            ),
            If(self.rising,
                If(self.cnt < 8, # Hold
                    NextValue(self.cnt, self.cnt + 1),
                    NextValue(self.din, self.din << 1)
                ).Else(
                    NextValue(self.so, 0)
                ) 
            ),
            If(self.falling,
                If(self.cnt < 8, # Setup
                    If(self.din[7],
                        NextValue(self.so, 1),
                    ).Else(
                        NextValue(self.so, 0),
                    )
                )
            )
        )

        self.sync += [
            If(self.falling, self.start.eq(0)),
            If(self.falling, self.done.eq(0))
        ]

class CascadingShifter(Module):
    def __init__(self):
        self.sck     = Signal()
        self.so      = Signal()
        self.si      = Signal()
        self.din     = Signal(8)
        self.dout    = Signal(8)
        self.start   = Signal()
        self.done    = Signal()

        edt = EdgeDetector()
        sti = ShifterIn()
        sto = ShifterOut()
        self.submodules += edt, sti, sto

        self.comb += [
            edt.s.eq(self.sck),
            sti.rising.eq(edt.r),
            sti.falling.eq(edt.f),
            sto.rising.eq(edt.r),
            sto.falling.eq(edt.f),
            sti.sck.eq(self.sck),
            sto.sck.eq(self.sck),
            sti.si.eq(self.si),
            self.so.eq(sto.so),
            sti.start.eq(self.start),
        ]

        self.sync += [
            If(edt.r, self.start.eq(0)),
            sto.start.eq(sti.done),
            If(sti.done, sto.din.eq(sti.dout)),
            self.done.eq(sto.done),
        ]

class TestEdgeDetector(Module):
    def __init__(self):
        self.inp     = Signal() # Signal input
        self.rising  = Signal() # Rising edge detect
        self.falling = Signal() # Falling edge detect

        # Create new debouncer and edge detect objects
        debouncer = Debouncer()
        edgedetect = EdgeDetector()
        
        # Include modules
        self.submodules += debouncer, edgedetect

        self.comb += [
            debouncer.i.eq(self.inp),
            edgedetect.s.eq(debouncer.o),
            self.rising.eq(edgedetect.r),
            self.falling.eq(edgedetect.f)
        ]

def ShifterInGenerator(dut):
    cnt1 = 0
    cnt2 = 0
    for cycle in range(1000):

        if cycle % 2 != 0:
            if cnt1 < 10:
                cnt1 = cnt1 + 1
            else:
                cnt1 = 0
                yield dut.sck.eq(~dut.sck)

        if cnt2 < 20:
            cnt2 = cnt2 + 1
        else:
            cnt2 = 0
            yield dut.si.eq(randrange(2))

        if cycle > 2 and cycle < 4:
            yield dut.start.eq(1)

        yield

def ShifterOutGenerator(dut):
    cnt1 = 0
    cnt2 = 0
    flag = 0
    onetime = 0
    for cycle in range(1000):

        if cycle % 2 != 0:
            if cnt1 < 10:
                cnt1 = cnt1 + 1
            else:
                cnt1 = 0
                yield dut.sck.eq(~dut.sck)
                flag = 1
                
        if cycle > 2 and cycle < 4:
            yield dut.din.eq(0xAA)

        # Need to generate start between pos & neg edge of sck
        if flag == 1 and onetime == 0:
            if cnt2 < 6:
                cnt2 += 1
            else:
                yield dut.start.eq(1)
                onetime = 1
        yield

def CascadingShifterGenerator(dut):
    cnt1 = 0
    cnt2 = 0
    for cycle in range(1000):

        if cycle % 2 != 0:
            if cnt1 < 10:
                cnt1 = cnt1 + 1
            else:
                cnt1 = 0
                yield dut.sck.eq(~dut.sck)

        if cnt2 < 20:
            cnt2 = cnt2 + 1
        else:
            cnt2 = 0
            yield dut.si.eq(randrange(2))
                
                
        if cycle > 2 and cycle < 4:
            yield dut.start.eq(1)

        yield


if __name__ == "__main__":
    #d = EdgeDetector()
    # print(verilog.convert(EdgeDetector()))
    # print(verilog.convert(EdgeDetector(), ios = {d.s}))
    #run_simulation(d, generator(d), clocks={"sys": 10}, vcd_name="EdgeDetector.vcd")

    #d = Debouncer()
    #run_simulation(d, generator(d), clocks={"sys": 10}, vcd_name="Debouncer.vcd")

    #t = TestEdgeDetector()
    #run_simulation(t, generator(t), clocks={"sys": 10}, vcd_name="TestEdgeDetector.vcd")

    #t = ShifterIn()
    #print(verilog.convert(ShifterIn()))
    #run_simulation(t, ShifterInGenerator(t), clocks={"sys": 10}, vcd_name="ShifterIn.vcd")
    #os.system("gtkwave ShifterIn.vcd")

    #t = ShifterOut()
    #print(verilog.convert(ShifterOut()))
    #run_simulation(t, ShifterOutGenerator(t), clocks={"sys": 10}, vcd_name="ShifterOut.vcd")
    #os.system("gtkwave ShifterOut.vcd")    

    t = CascadingShifter()
    #print(verilog.convert(CascadingShifter()))
    run_simulation(t, CascadingShifterGenerator(t), clocks={"sys": 10}, vcd_name="CascadingShifter.vcd")
    os.system("gtkwave CascadingShifter.vcd")

    