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

extern uint32_t sram;
    // NOTE: a pointer to this is a null pointer,
    // but the compiler does not know that because
    // "sram" is a linker symbol from sections.lds.

struct _reent reent_struct;
struct _reent *_impure_ptr __ATTRIBUTE_IMPURE_PTR__;


// --------------- Function Prototypes ----------------

void set_leds_init_begin_state(void);
void set_leds_init_end_state(void);
void init_user_comms(void);
void check_and_handle_reboot_due_to_overflow(void);
void check_and_handle_terminal_init_due_to_reboot(void);


// ----------------------- Main  ----------------------

int main(void)
{
    int ret;


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

    uart_write_string_with_prompts(e_no_cpu_prompt, e_system_clock,
                                        "initialize memory...", REPL_MODE);
    initialise_memory(e_print_none, REPL_MODE);
    uart_write_string("done."STR_NL_CR);

    uart_write_string_with_prompts(e_no_cpu_prompt, e_system_clock,
                                        "initialize I/O...", REPL_MODE);
    init_io();
    uart_write_string("done."STR_NL_CR);

    uart_write_string_with_prompts(e_no_cpu_prompt, e_system_clock, "initialize flash...", REPL_MODE);
    init_flash();
    uart_write_string("done."STR_NL_CR);

    _impure_ptr = &reent_struct;

    set_board_led_state(e_led5, e_off);

    set_board_leds_hw_mode();
        // NOTE: let hardware take control of
        // our LEDs...


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