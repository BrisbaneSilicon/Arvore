#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>

#include "global.h"
#include "config.h"
#include "stdlib.h"
#include "io.h"
#include "flash.h"
#include "interrupt.h"
#include "memory_gowin.h"


// ---------------------- Defines ----------------------


// ---------- Global Variables / Constants ------------


// --------------- Function Prototypes ----------------

void set_leds_init_begin_state(void);
void set_leds_init_end_state(void);
void init_user_comms(void);
void check_and_handle_reboot_due_to_overflow(void);
void check_and_handle_terminal_init_due_to_reboot(void);


// ----------------------- Main  ----------------------

int main(void)
{
    // NOTE: initialize LEDs

    set_leds_init_begin_state();


    // NOTE: initialize library

    read_cpu_freq();
    read_core_info();
    read_uart_cfg();
    read_general_timer_cfg();
    read_performance_timer_cfg();


    // NOTE: initialise UART,
    // required by stack overflow
    // / reboot comms ...

    init_user_comms();

    check_and_handle_reboot_due_to_overflow();
    check_and_handle_terminal_init_due_to_reboot();

    uart_write_string("Initialize memory...");
    initialise_memory(e_print_none, REPL_MODE);
    uart_write_string("done."STR_NL_CR);

    uart_write_string("Initialize I/O...");
    init_io();
    uart_write_string("done."STR_NL_CR);

    uart_write_string("Initialize flash...");
    init_flash();
    uart_write_string("done."STR_NL_CR);


    // NOTE: user code goes here...


    while(1);
        // NOTE: just to squash warnings...
        // feel free to delete.

    return 0;
}

void reboot(void)
{
    UTILS0->FIRMWARE_VERSION = 0x80000000;

    // NOTE: won't get here!
    while(1);
}

void check_and_handle_reboot_due_to_overflow(void)
{
    if(was_reboot_due_to_stack_overflow()) {
        uart_write_string(STR_NL_CR STR_NL_CR "fatal error: runtime: stack overflow");

        while(1);
    }
}

void check_and_handle_terminal_init_due_to_reboot(void)
{
    if (get_successfully_booted_hardware_flag()) {
        // NOTE: we've booted in the past, so
        // this is a reboot...

        clear_console_and_history_and_reset_cursor();
    }
}

void set_leds_init_begin_state(void)
{
    UTILS0->BOARD_LED_OUT_WO = 0x00;
}

void set_leds_init_end_state(void)
{
    UTILS0->BOARD_LED_OUT_WO = 0xFF;
}

void init_user_comms(void)
{
    uart_init();

    set_color_for_repl_mode();
}

void irqCallback(void)
{
    ;
}