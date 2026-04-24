#ifndef INTERRUPT_H
#define INTERRUPT_H

#define SW_INTERRUPT_STR    "SW_INTRPTS"

#define HW_BUFFER           "HW_BUFFER"


typedef enum {
    e_gpio_intrpt_btflg_gnd             = 0x01,
    e_gpio_intrpt_btflg_vcc             = 0x02,
    e_gpio_intrpt_btflg_rising_edge     = 0x04,
    e_gpio_intrpt_btflg_falling_edge    = 0x08
} e_gpio_interrupt_bitflags;

typedef enum {
    e_uart_rx_intrpt_btflg_rx_data      = 0x01
} e_uart_rx_interrupt_bitflags;


#endif