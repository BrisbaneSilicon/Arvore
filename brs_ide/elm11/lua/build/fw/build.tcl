set workspace_path  [lindex $argv 0]

set hardware_path   "$workspace_path/hardware"
set build_path      "$hardware_path/.build"

create_project -name "emblua" -dir . -pn "GW1NR-LV9QN88PC7/I6" -device_version "C" -force

set_option -verilog_std         sysv2017
set_option -vhdl_std            vhd2008
set_option -use_sspi_as_gpio    1
set_option -use_mspi_as_gpio    1
set_option -place_option        2
set_option -replicate_resources 1
set_option -clock_route_order   1
set_option -route_option        1
set_option -use_done_as_gpio    1

add_file "$build_path/emblua.vg"
add_file "$build_path/location.cst"
add_file "$build_path/timing.sdc"

if {[file exists "$hardware_path/user.sv"]} {
    add_file "$hardware_path/user.sv"
}
if {[file exists "$hardware_path/user.vhd"]} {
    add_file "$hardware_path/user.vhd"
}

set_option -top_module emblua

run all
