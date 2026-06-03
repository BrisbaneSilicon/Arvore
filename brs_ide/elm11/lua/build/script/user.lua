--[[
        Demonstrate Application, Driver and Hardware layers

        NOTE:
--]]

program_name = "User Example"


-- Program dependencies

import('all')
    -- NOTE: import entire base library

import('string', 'format')
import('table', 'insert')
    -- NOTE: import functions from specific
    -- libraries

import('user', 'quick_toggle')
import('user', 'lfsr32_next')
import('user', 'is_even')
import('user', 'hw_lfsr32')
    -- NOTE: import example API functions
    -- from driver


-- Program configuration

QUICK_TOGGLE_PIN = 1


-- Main program begin

print("\n -------- Program begin: "..program_name.." --------\n")
msleep(500)

print("Lua Version: ".._VERSION.."\n")
msleep(500)

print("Driver Version: ".._sW)
print("Hardware Version: ".._fW.."\n")
msleep(500)


-- Initialise PINS

print("Initialise PINs")

reset_all_io_type_cfg()
set_io_type_cfg(QUICK_TOGGLE_PIN, GPIO_OUT)


-- Perform Quick toggle

print("Performing quick toggle of PIN"..QUICK_TOGGLE_PIN.."\n")

user.quick_toggle(QUICK_TOGGLE_PIN)
msleep(500)


-- Perform Driver-based LFSR

print("Performing driver-based LFSR32 calculation")
print("pre, post")

local curr = 1
local even_taps = {}
for i=1,31 do
    curr, prev = user.lfsr32_next(curr)
    print("  "..prev..", "..curr)

    even = user.is_even(curr)
    if even then
        table.insert(even_taps, prev)
    end
end
msleep(500)

print("\nFound XOR-Taps (bits 1, 8, 22 and 24) evenly asserted for pre-lfsr arguments:")
for _, value in ipairs(even_taps) do
    print("  "..value)
end
msleep(500)


-- Perform Hardware-based LFSR

print("\nPerforming hardware-based LFSR32 calculation")

hw_write(0, 0)
    -- NOTE: reset the LFSR (write of
    -- any value to any address)
for i=1,31 do
    print("  "..user.hw_lfsr32())
end
msleep(500)


-- Perform Hardware ID check

print("\nPerforming hardware ID check")

id = hw_read(0)
print(string.format("Hardware ID=0x%.8x", id))
if id == 0xdeadbeef then
    print("Workspace default HDL is 'SystemVerilog'")
elseif id == 0x8badf00d then
    print("Workspace default HDL is 'VHDL'")
else
    print("Workspace default unknown - you've modified 'user.sv/vhd'...")
end
msleep(500)


-- Main program end

print("\n -------- Program end: "..program_name.." --------\n")