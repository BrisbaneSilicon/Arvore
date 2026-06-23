create_clock -name clk_27Mhz        -period 37.037  -waveform {0 18.518}    [get_ports  {pad_clk_27Mhz}]

create_clock -name clk_60Mhz        -period 16.500  -waveform {0 8.250}     [get_pins   {emblua_top_inst/clk66mhz_inst/rpll_inst/CLKOUT}]
create_clock -name clk_60Mhz_p      -period 16.500  -waveform {0 8.250}     [get_pins   {emblua_top_inst/clk66mhz_inst/rpll_inst/CLKOUTP}]


# NOTE: all clocks, to/from everything else

set_false_path -from [get_clocks {clk_27Mhz}]       -to [get_clocks {clk_60Mhz}]
set_false_path -from [get_clocks {clk_60Mhz}]       -to [get_clocks {clk_27Mhz}]

set_false_path -from [get_clocks {clk_27Mhz}]       -to [get_clocks {clk_60Mhz_p}]
set_false_path -from [get_clocks {clk_60Mhz_p}]     -to [get_clocks {clk_27Mhz}]

set_false_path -from [get_clocks {clk_60Mhz}]       -to [get_clocks {clk_60Mhz_p}]
set_false_path -from [get_clocks {clk_60Mhz_p}]     -to [get_clocks {clk_60Mhz}]
