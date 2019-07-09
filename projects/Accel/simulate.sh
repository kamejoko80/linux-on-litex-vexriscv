#!/bin/sh


# cleanup
rm -rf obj_dir
rm -f  accel.vcd


# run Verilator to translate Verilog into C++, include C++ testbench
verilator -Wall --cc --trace accel.v --exe accel_tb.cpp
# build C++ project
make -j -C obj_dir/ -f Vaccel.mk Vaccel
# run executable simulation
obj_dir/Vaccel


# view waveforms
gtkwave accel.vcd accel.sav &

