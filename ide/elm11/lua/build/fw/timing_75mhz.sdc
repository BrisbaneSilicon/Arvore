create_clock -name clk_27Mhz        -period 37.037  -waveform {0 18.518}    [get_ports  {pad_clk_27Mhz}]

create_clock -name clk_75Mhz        -period 12.500  -waveform {0 6.250}     [get_pins   {emblua_top_inst/clk75mhz_inst/rpll_inst/CLKOUT}]
create_clock -name clk_75Mhz_p      -period 12.500  -waveform {0 6.250}     [get_pins   {emblua_top_inst/clk75mhz_inst/rpll_inst/CLKOUTP}]
    # NOTE: for consistent functioning, I've
    # found that I needed to drop the clock
    # period to a bit below what it actually
    # is... their PAR must be a bit dodgy...

# NOTE: all clocks, to/from everything else

set_false_path -from [get_clocks {clk_27Mhz}]       -to [get_clocks {clk_75Mhz}]
set_false_path -from [get_clocks {clk_75Mhz}]       -to [get_clocks {clk_27Mhz}]

set_false_path -from [get_clocks {clk_27Mhz}]       -to [get_clocks {clk_75Mhz_p}]
set_false_path -from [get_clocks {clk_75Mhz_p}]     -to [get_clocks {clk_27Mhz}]

set_false_path -from [get_clocks {clk_75Mhz}]       -to [get_clocks {clk_75Mhz_p}]
set_false_path -from [get_clocks {clk_75Mhz_p}]     -to [get_clocks {clk_75Mhz}]
