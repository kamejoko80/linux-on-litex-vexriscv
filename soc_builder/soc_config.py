
soc_config = {

    # Soc Name -----------------------------------------------------------------
    "soc_name":    "soc_01",    # SoC name
    "ident":       "1",         # SoC indentify

    # General ------------------------------------------------------------------
    "cpu":         "vexriscv",  # Type of CPU used for init/calib (vexriscv, lm32)
    "cpu_variant": "minimal",   # CPU variant
    "speedgrade":  -1,          # FPGA speedgrade

    # Frequency ----------------------------------------------------------------
    "input_clk_freq":   100e6,  # Input clock frequency
    "sys_clk_freq":     100e6,  # System clock frequency (DDR_clk = 4 x sys_clk)
    "iodelay_clk_freq": 200e6,  # IODELAYs reference clock frequency

    # Memory -------------------------------------------------------------------
    "rom_size":         32768,  # Integrated rom size
    "sram_size":        4096,   # Integrated sram size
}
