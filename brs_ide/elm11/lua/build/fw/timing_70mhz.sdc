create_clock -name clk_27Mhz        -period 37.037  -waveform {0 18.518}    [get_ports  {pad_clk_27Mhz}]

create_clock -name clk_70Mhz        -period 14.000  -waveform {0 7.000}     [get_pins   {emblua_top_inst/clk70mhz_inst/rpll_inst/CLKOUT}]
create_clock -name clk_70Mhz_p      -period 14.000  -waveform {0 7.000}     [get_pins   {emblua_top_inst/clk70mhz_inst/rpll_inst/CLKOUTP}]
    # NOTE: for consistent functioning, I've
    # found that I needed to drop the clock
    # period to a bit below what it actually
    # is... their PAR must be a bit dodgy...

# NOTE: all clocks, to/from everything else

set_false_path -from [get_clocks {clk_27Mhz}]       -to [get_clocks {clk_70Mhz}]
set_false_path -from [get_clocks {clk_70Mhz}]       -to [get_clocks {clk_27Mhz}]

set_false_path -from [get_clocks {clk_27Mhz}]       -to [get_clocks {clk_70Mhz_p}]
set_false_path -from [get_clocks {clk_70Mhz_p}]     -to [get_clocks {clk_27Mhz}]

set_false_path -from [get_clocks {clk_70Mhz}]       -to [get_clocks {clk_70Mhz_p}]
set_false_path -from [get_clocks {clk_70Mhz_p}]     -to [get_clocks {clk_70Mhz}]