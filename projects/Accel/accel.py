import os
from migen import *
from migen.fhdl import verilog
from random import randrange

class Accel(Module):
    def __init__(self, sck_i, sdi_i, sdo_o, csn_i):
        # Define new clock domain
        self.clock_domains.cd_sckn = ClockDomain("sckn", reset_less=True)
        self.clock_domains.cd_sckp = ClockDomain("sckp", reset_less=True)
        self.clock_domains.cd_csni = ClockDomain("csni", reset_less=True)
        
        # Connect clock domain
        self.comb += self.cd_sckn.clk.eq(~sck_i)
        self.comb += self.cd_sckp.clk.eq(sck_i)
        self.comb += self.cd_csni.clk.eq(~csn_i)
        
        self.reg_i = Signal(8)
        self.cnt   = Signal(8)
        self.cmd   = Signal(2) # cmd = {0, 1, 2, 3} invalid, reg read, reg write, fifo read 
        
        # Reset counter when csn_i low
        self.sync.csni += [
            self.reg_i.eq(0),
            self.cnt.eq(0),
            self.cmd.eq(0),
        ]

        # Read sdi_i
        self.sync.sckp += [
            If((self.cnt < 8) & ~csn_i,
               self.cnt.eq(self.cnt + 1),            
               If(sdi_i, 
                    self.reg_i[0].eq(1)
               ).Else(
                    self.reg_i[0].eq(0)
               )
            )
        ]

        # Shift bit
        self.sync.sckn += [
            If( ~csn_i,
               If(self.cnt < 8,
                  self.reg_i.eq(self.reg_i << 1)                  
               ).Elif(self.cnt == 8, 
                     If(self.reg_i == 0x0B, 
                        self.cmd.eq(1) # Read Register
                     ).Elif(self.reg_i == 0x0A, 
                        self.cmd.eq(2) # Write Register
                     ).Elif(self.reg_i == 0x0D, 
                        self.cmd.eq(3) # Read FIFO data
                     ).Else(
                        self.cmd.eq(0) # Invalide command
                     )  
               ) 
            )
        ]

#Simulation and verilog conversion
sck_i  = Signal()
sdi_i  = Signal()
sdo_o  = Signal()
csn_i  = Signal()
        
def generator(dut):
    for i in range(5000):
        yield sdi_i.eq(randrange(2))
        yield sck_i.eq(~sck_i)
        if i > 3:
            yield csn_i.eq(0)
        else:
            yield csn_i.eq(1)
        yield       
        
if __name__ == "__main__":
    ac = Accel(sck_i, sdi_i, sdo_o, csn_i)
    print(verilog.convert(Accel(sck_i, sdi_i, sdo_o, csn_i), ios = {sck_i, sdi_i, sdo_o, csn_i}))
    #run_simulation(ac, generator(ac), clocks={"sys": 10}, vcd_name="accel.vcd") 