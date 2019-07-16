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

class RegisterArray(Module):
    def __init__(self):
        self.addr   = Signal(8)
        self.dw     = Signal(8)
        self.dr     = Signal(8)
        self.r      = Signal()
        self.w      = Signal()

        # Register set
        self.reg0   = Signal(8, reset=0xAD)
        self.reg1   = Signal(8, reset=0x1D)
        self.reg2   = Signal(8, reset=0xF2)

        self.sync += [
            If(self.r,
                Case(self.addr, {
                    0: self.dr.eq(self.reg0),
                    1: self.dr.eq(self.reg1),
                    2: self.dr.eq(self.reg2),
                })
            ).Elif(self.w,
                Case(self.addr, {
                    0: self.reg0.eq(self.dw),
                    1: self.reg1.eq(self.dw),
                    2: self.reg2.eq(self.dw),
                })
            )
        ]

class Control(Module):
    def __init__(self):
        # Physical pin signals
        self.sck     = Signal()
        self.so      = Signal()
        self.si      = Signal()
        self.csn     = Signal(1, reset=1)

        # Input signals interface
        self.dout    = Signal(8)
        self.si_done = Signal()
        self.so_done = Signal()
        self.start   = Signal()

        # Output signals interface
        self.addr     = Signal(8)
        self.dw       = Signal(8)
        self.dr       = Signal(8)
        self.r        = Signal()
        self.w        = Signal()

        # Internal registers
        self.str_addr = Signal(8)
        self.str_cmd  = Signal(8)
        self.cnt      = Signal(8)
        self.reg_done = Signal()

        # Define edgedetecter, shifter in/out
        edt1 = EdgeDetector()
        edt2 = EdgeDetector()
        sti = ShifterIn()
        sto = ShifterOut()
        self.submodules += edt1, edt2, sti, sto

        # Connect to edgedetecter, shifter in/out
        self.comb += [
            edt1.s.eq(self.sck),
            sti.rising.eq(edt1.r),
            sti.falling.eq(edt1.f),
            sto.rising.eq(edt1.r),
            sto.falling.eq(edt1.f),
            sti.sck.eq(self.sck),
            sto.sck.eq(self.sck),
            sti.si.eq(self.si),
            self.so.eq(sto.so),
            edt2.s.eq(self.csn),
        ]

        # Connect to register set
        reg = RegisterArray()
        self.submodules += reg

        self.comb += [
            reg.addr.eq(self.addr),
            reg.r.eq(self.r),
            reg.w.eq(self.w),
            reg.dw.eq(self.dw),
            self.dr.eq(reg.dr),
        ]

        fsm = FSM(reset_state = "IDLE")
        self.submodules += fsm

        fsm.act("IDLE",
            If(edt2.f, # csn falling edge
                NextValue(self.cnt, 0),
                NextState("START"),
            )
        )
        fsm.act("START",
            If(self.cnt >= 2,
                NextValue(self.start, 1),
            ).Else(
                 NextValue(self.cnt, self.cnt + 1),
            ),
            If(self.start,
                NextValue(self.start, 0),
                NextValue(sti.done, 0),
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
            If(self.str_cmd == 0x0A, # Reg write
                NextValue(sti.done, 0),
                NextValue(sti.start, 1),
                NextState("REG_ADDR"),
            ).Elif(self.str_cmd == 0x0B, # Reg read
                NextValue(sti.done, 0),
                NextValue(sti.start, 1),
                NextState("REG_ADDR"),
            ).Elif(self.str_cmd == 0x0D, # FIFO read
                NextState("READ_FIFO"),
            ).Else(
                NextState("IDLE"),
            )
        )
        fsm.act("REG_ADDR",
            If(sti.done,
                NextValue(self.str_addr, sti.dout),
                NextState("DETERMINE_REG_ACCESS"),
            )
        )
        fsm.act("DETERMINE_REG_ACCESS",
            If(self.str_cmd == 0x0A, # Reg write
                NextValue(sti.done, 0),
                NextValue(sti.start, 1),
                NextState("REG_VALUE_SHIFTIN"),
            ).Elif(self.str_cmd == 0x0B, # Reg read
                NextValue(self.addr, self.str_addr),
                NextValue(self.r, 1),
                NextState("REG_READ_STROBE"),
            ).Else(
                NextState("IDLE"),
            )
        )
        fsm.act("REG_VALUE_SHIFTIN",
            If(sti.done,
                NextValue(self.dw, sti.dout),
                NextValue(self.w, 1),
                NextState("REG_WRITE_STROBE"),
            )
        )
        fsm.act("REG_WRITE_STROBE",
            NextState("REG_WRITE_VALUE"),
        )
        fsm.act("REG_WRITE_VALUE",
            NextValue(self.w, 0),
            NextState("IDLE"),
        )
        fsm.act("REG_READ_STROBE",
            NextState("LOAD_SHIFT_OUT_DATA"),
        )
        fsm.act("LOAD_SHIFT_OUT_DATA",
            NextValue(sto.din, self.dr),
            NextState("START_SHIFT_OUT"),
        )
        fsm.act("START_SHIFT_OUT",
            NextValue(self.r, 0),
            NextValue(sto.done, 0),
            NextValue(sto.start, 1),
            NextState("SHIFTING_OUT"),
        )
        fsm.act("SHIFTING_OUT",
            If(sto.done,
                NextState("SHIFT_OUT_DONE"),
            )
        )
        fsm.act("SHIFT_OUT_DONE",
            If(edt2.r | self.csn, # csn rising edge
                NextState("IDLE"),
            ).Elif(self.addr < 0x2D,
                NextValue(self.addr, self.addr + 1),
                NextValue(self.r, 1),
                NextState("REG_READ_STROBE"),
            ).Else(
                NextState("IDLE"),
            )
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

def ControlReadRegGenerator(dut):
    t = 3  # Number of si transfer byte
    u = 5  # Number of shifted byte
    s = 4  # SCK toggle at cycle 4th
    n = 10 # n cycles per sck toggle
    i = 0
    j = 0
    cmd_addr = 0x0B00

    for cycle in range(1000):
        # Generate si
        if cycle == (s + j*n*2) and j < 2*8*t:
            if (cmd_addr & 0x8000):
                yield dut.si.eq(1)
            else:
                yield dut.si.eq(0)
            cmd_addr = cmd_addr << 1
            j = j + 1
        # Generate sck
        if cycle == (s + n/2 + i*n) and i < 2*8*u:
            yield dut.sck.eq(~dut.sck)
            i = i + 1
        elif i >= 2*8*u:
            yield dut.csn.eq(1)

        if cycle > 1 and cycle < 3:
            yield dut.csn.eq(0)

        yield

def ControlWriteRegGenerator(dut):
    t = 3  # Number of si transfer byte
    u = 3  # Number of shifted byte
    s = 4  # SCK toggle at cycle 4th
    n = 10 # n cycles per sck toggle
    i = 0
    j = 0
    cmd_addr = 0x0A0155

    for cycle in range(1000):
        # Generate si
        if cycle == (s + j*n*2) and j < 2*8*t:
            if (cmd_addr & 0x800000):
                yield dut.si.eq(1)
            else:
                yield dut.si.eq(0)
            cmd_addr = cmd_addr << 1
            j = j + 1
        # Generate sck
        if cycle == (s + n/2 + i*n) and i < 2*8*u:
            yield dut.sck.eq(~dut.sck)
            i = i + 1

        if cycle > 1 and cycle < 3:
            yield dut.csn.eq(0)

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
    #print(verilog.convert(Control()))
    run_simulation(t, ControlReadRegGenerator(t), clocks={"sys": 10}, vcd_name="Control.vcd")
    #run_simulation(t, ControlWriteRegGenerator(t), clocks={"sys": 10}, vcd_name="Control.vcd")
    os.system("gtkwave Control.vcd")
    