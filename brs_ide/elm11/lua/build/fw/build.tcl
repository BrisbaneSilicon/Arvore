create_project -name "emblua" -dir . -pn "GW1NR-LV9QN88PC7/I6" -device_version "C" -force

set_option -verilog_std sysv2017
set_option -vhdl_std vhd2008
set_option -use_sspi_as_gpio 1
set_option -use_mspi_as_gpio 1
set_option -place_option 2
set_option -replicate_resources 1
set_option -clock_route_order 1
set_option -route_option 1
set_option -use_done_as_gpio 1

add_file "emblua.vg"
add_file "location.cst"
add_file "timing.sdc"

if {[file exists "user.sv"]} {
    add_file "user.sv"
}
if {[file exists "user.vhd"]} {
    add_file "user.vhd"
}

set_option -top_module emblua

run all
