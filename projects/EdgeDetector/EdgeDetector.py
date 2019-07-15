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

class Register(Module):
    def __init__(self, addr=0):
        self.reg    = Signal(8)
        self.addr   = Signal(8)
        self.dw     = Signal(8)
        self.dr     = Signal(8)
        self.r      = Signal()
        self.w      = Signal()

        self.sync += [
            If(self.addr == addr,
                If(self.w,
                    self.reg.eq(self.dw)
                ).Elif(self.r,
                    self.dr.eq(self.reg)
                )
            )
        ]

class Control(Module):
    def __init__(self):
        # Physical pin signals
        self.sck     = Signal()
        self.so      = Signal()
        self.si      = Signal()

        # Input signals interface
        self.dout    = Signal(8)
        self.si_done = Signal()
        self.so_done = Signal()
        self.start   = Signal()

        # Output signals interface
        self.din      = Signal(8)
        self.addr     = Signal(8)
        self.dw       = Signal(8)
        self.dr       = Signal(8)
        self.r        = Signal()
        self.w        = Signal()
        self.si_start = Signal()
        self.so_start = Signal()

        # Internal registers
        self.str_addr = Signal(8)
        self.str_data = Signal(8)
        self.str_cmd  = Signal(8)

        # Define edgedetecter, shifter in/out
        edt = EdgeDetector()
        sti = ShifterIn()
        sto = ShifterOut()
        self.submodules += edt, sti, sto

        # Connect to edgedetecter, shifter in/out 
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
            #sti.start.eq(self.si_start),
            #sto.start.eq(self.so_start),
        ]

        # Connect to register set
        reg0 = Register(addr = 0x00)
        reg1 = Register(addr = 0x01)
        reg2 = Register(addr = 0x02)

        self.submodules += reg0, reg1, reg2

        self.comb += [
            # Reg0
            reg0.addr.eq(self.addr),
            reg0.r.eq(self.r),
            reg0.w.eq(self.w),
            reg0.dw.eq(self.dw),
            self.dr.eq(reg0.dr),
            # Reg1
            reg1.addr.eq(self.addr),
            reg1.r.eq(self.r),
            reg1.w.eq(self.w),
            reg1.dw.eq(self.dw),
            self.dr.eq(reg1.dr),
            # Reg2
            reg1.addr.eq(self.addr),
            reg1.r.eq(self.r),
            reg1.w.eq(self.w),
            reg1.dw.eq(self.dw),
            self.dr.eq(reg1.dr),
        ]

        fsm = FSM(reset_state = "IDLE")
        self.submodules += fsm
        
        fsm.act("IDLE",
            If(self.start,
                NextValue(self.start, 0),
                NextValue(sti.start, 1),
                NextState("GET_COMMAND"),
            )
        )        
        fsm.act("GET_COMMAND",
            If(sti.done,
                NextValue(self.str_cmd, sti.dout),
                NextState("CMD_DECODE"),
            )
        )        
        fsm.act("CMD_DECODE",
            If(self.str_addr == 0x0A, # Reg write
                NextValue(sti.start, 1),
                NextState("REG_ADDR"),                
            ).Elif(self.str_addr == 0x0B, # Reg read
                NextValue(sti.start, 1),
                NextState("REG_ADDR"),
            ).Elif(self.str_addr == 0x0D, # Reg read
                NextState("READ_FIFO"),
            ).Else(
                NextState("IDLE"),
            )
        )
        fsm.act("REG_ADDR",
            If(sti.done,
                NextValue(self.str_addr, sti.dout),
                NextState("REG_ACCESS"),
            )
        )
        fsm.act("REG_ACCESS",
            If(self.str_addr == 0x0A, # Reg write
                NextValue(sti.start, 1),
                NextState("REG_DATA"),
            ).Elif(self.str_addr == 0x0B, # Reg read
                NextValue(self.addr, self.str_addr),
                NextValue(self.r, 1),
                NextState("REG_READ"),
            ).Else(
                NextState("IDLE"),
            )
        )
        fsm.act("REG_DATA",
            If(sti.done,
                NextValue(self.w, sti.dout),
                NextValue(self.w, 1),
                NextState("IDLE"),
            )
        )
        fsm.act("REG_READ",
            NextValue(sto.din, self.dr),
            NextValue(sto.start, 1),
            NextState("IDLE"),
        )
        fsm.act("READ_FIFO",

        )

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

def ControlGenerator(dut):
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

    #t = CascadingShifter()
    #print(verilog.convert(CascadingShifter()))
    #run_simulation(t, CascadingShifterGenerator(t), clocks={"sys": 10}, vcd_name="CascadingShifter.vcd")
    #os.system("gtkwave CascadingShifter.vcd")

    t = Control()
    # print(verilog.convert(Control()))
    run_simulation(t, ControlGenerator(t), clocks={"sys": 10}, vcd_name="Control.vcd")
    os.system("gtkwave Control.vcd")    
    