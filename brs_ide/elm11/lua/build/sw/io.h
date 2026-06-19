#ifndef IO_H
#define IO_H

#include "global.h"
#include "config.h"

#include "global.h"
#include "printf.h"
#include "flash.h"


// ---------------------- Defines ----------------------

#define PWM_VALUE_MAX                                           (256)

#define DEFAULT_UART_BAUD                                       (9600)

#define PMW_FREQ_KHZ_MAX                                        (255)
#define DEFAULT_PWM_FREQ_KHZ                                    (10)

#define SPI_FREQ_KHZ_MAX                                        (255)
#define DEFAULT_SPI_FREQ_KHZ                                    (10)

#define FPGA_IO_CONF_SPI_ORDER_BITFLAG                          (1 << 13)

#define FPGA_IO_CONF_SUPPORTS_SOFTWARE_INTERRUPTS_BITFLAG       (1 << 16)
#define FPGA_IO_CONF_SUPPORTS_SMALL_HARDWARE_BUFFER_BITFLAG     (1 << 17)
#define FPGA_IO_CONF_SUPPORTS_LARGE_HARDWARE_BUFFER_BITFLAG     (1 << 18)

#define FPGA_SHARED_SPI_SUPPORTED_BITFLAG                       (1 << 0)
#define FPGA_SHARED_SPI_PIN_ORDER_BITFLAG                       (1 << 1)


// ----------------- Typedefs / Enums ------------------

typedef enum e_iotype
{
    e_none      = 0,
    e_gpio_out,
    e_gpio_in,
    e_pwm,
    e_uart_out,
    e_uart_in,
    e_spi_out,
    e_spi_in,
    e_i2c,
        // NOTE: add new I/O types here...
        // NOTE: add new 'FPGA_IO_CONF_SUPPORTS_' if a
        // new I/O type is added...

    e_total_standalone_io_types,

    // NOTE: these are all in-direct config,
    // i.e. associated clocks, chip-select etc
    e_spi_out_rel1,
        // NOTE: relational type - either
        // SPI_CLK or SPI_CS
    e_spi_out_rel2,
    e_spi_in_rel1,
    e_spi_in_rel2,
    e_i2c_rel1, // NOTE: SCL

    e_invalid
} e_iotype;

typedef enum e_analogtype
{
    e_analog_none       = e_invalid + 1,
    e_analog_adc_in,
    e_analog_dac_out,

    e_total_analog_type_index_limit
} e_analogtype;

typedef enum e_relational_iotype
{
    e_spi_out_clk   = 0,
    e_spi_out_cs,
    e_spi_in_clk,
    e_spi_in_cs
} e_relational_iotype;

typedef enum e_status
{
    e_success               = 0,
    e_function_call_error,
    e_invalid_io_number,
    e_invalid_config,
    e_invalid_sw_int_config,
    e_io_currently_locked,
    e_io_doesnt_support_config,
    e_invalid_argument,
    e_total_status
} e_status;

typedef enum e_io_level
{
    e_level_low      = 0,
    e_level_high,
    e_level_toggle
} e_io_level;

typedef enum e_io_numbers
{
    e_pin1      = 1,
    e_pin2,
    e_pin3,
    e_pin4,
    e_pin5,
    e_pin6,
    e_pin7,
    e_pin8,
    e_pin9,
    e_pin10,
    e_pin11,
    e_pin12,
    e_pin13,
    e_pin14,
    e_pin15,
    e_pin16,
    e_pin17,
    e_pin18,
    e_pin19,
    e_pin20,
    e_pin21,
    e_pin22,
    e_pin23,
    e_pin24,
    e_pin25,
    e_pin26,
    e_pin27,
    e_pin28,
    e_pin29,
    e_pin30,
    e_pin31,
    e_pin32,
    e_total_io
} e_io_numbers;

typedef enum e_io_bitmasks
{
    e_pin1_bitmask      = 0x00000001,
    e_pin2_bitmask      = 0x00000002,
    e_pin3_bitmask      = 0x00000004,
    e_pin4_bitmask      = 0x00000008,
    e_pin5_bitmask      = 0x00000010,
    e_pin6_bitmask      = 0x00000020,
    e_pin7_bitmask      = 0x00000040,
    e_pin8_bitmask      = 0x00000080,
    e_pin9_bitmask      = 0x00000100,
    e_pin10_bitmask     = 0x00000200,
    e_pin11_bitmask     = 0x00000400,
    e_pin12_bitmask     = 0x00000800,
    e_pin13_bitmask     = 0x00001000,
    e_pin14_bitmask     = 0x00002000,
    e_pin15_bitmask     = 0x00004000,
    e_pin16_bitmask     = 0x00008000,
    e_pin17_bitmask     = 0x00010000,
    e_pin18_bitmask     = 0x00020000,
    e_pin19_bitmask     = 0x00040000,
    e_pin20_bitmask     = 0x00080000,
    e_pin21_bitmask     = 0x00100000,
    e_pin22_bitmask     = 0x00200000,
    e_pin23_bitmask     = 0x00400000,
    e_pin24_bitmask     = 0x00800000,
    e_pin25_bitmask     = 0x01000000,
    e_pin26_bitmask     = 0x02000000,
    e_pin27_bitmask     = 0x04000000,
    e_pin28_bitmask     = 0x08000000,
    e_pin29_bitmask     = 0x10000000,
    e_pin30_bitmask     = 0x20000000,
    e_pin31_bitmask     = 0x40000000,
    e_pin32_bitmask     = 0x80000000
} e_io_bitmasks;

typedef enum e_hw_buf_type_t
{
    e_hw_buf_none       = 0,
    e_hw_buf_small,
    e_hw_buf_large,
} e_hw_buf_type_t;
    // NOTE: hw == hardware
    // NOTE: buf == buffer

typedef enum e_pin_enable_state
{
    e_pin_disabled  = 0,
    e_pin_enabled
} e_pin_enable_state;


// ---------------------- Defines (enum dependent) ----------------------

#define FPGA_IO_CONF_SUPPORTS_GPIO_OUT_BITFLAG                  (1 << e_gpio_out)
#define FPGA_IO_CONF_SUPPORTS_GPIO_IN_BITFLAG                   (1 << e_gpio_in)
#define FPGA_IO_CONF_SUPPORTS_PWM_BITFLAG                       (1 << e_pwm)
#define FPGA_IO_CONF_SUPPORTS_UART_OUT_BITFLAG                  (1 << e_uart_out)
#define FPGA_IO_CONF_SUPPORTS_UART_IN_BITFLAG                   (1 << e_uart_in)
#define FPGA_IO_CONF_SUPPORTS_SPI_OUT_BITFLAG                   (1 << e_spi_out)
#define FPGA_IO_CONF_SUPPORTS_SPI_IN_BITFLAG                    (1 << e_spi_in)
#define FPGA_IO_CONF_SUPPORTS_I2C_BITFLAG                       (1 << e_i2c)


// --------------- Function Prototypes ----------------

void init_io(void);

uint8_t io_get_num_pins(void);
uint8_t update_io_type(uint16_t io_index, e_iotype io_type);
const char* get_io_type_as_str(uint16_t io_index);
uint16_t user_io_num_from_str(char *user_io_num_str) ATTRIB_F1CODE;

uint8_t is_hardware_shared_spi_config(void) ATTRIB_F1CODE;

e_iotype get_smallest_index_dynamic_iotype_offset(void) ATTRIB_F1CODE;
e_iotype get_max_iotypes(void) ATTRIB_F1CODE;
e_iotype get_io_type(uint32_t user_io_num) ATTRIB_F1CODE;

uint8_t valid_user_io_num(uint16_t user_io_num) ATTRIB_F1CODE;
uint8_t valid_user_io_num_as_str(char *user_io_num_str) ATTRIB_F1CODE;
uint8_t valid_formatting_for_user_io_num_as_str(char *user_io_num_str) ATTRIB_F1CODE;
uint8_t valid_io_type_as_str(char *io_type_str) ATTRIB_F1CODE;
uint8_t valid_standalone_io_type(e_iotype io_type) ATTRIB_F1CODE;

uint8_t valid_io_baud(uint32_t baud_rate) ATTRIB_F1CODE;
uint8_t can_set_baud_for_io_type(e_iotype iotype) ATTRIB_F1CODE;
uint8_t is_baud_config_applicable_to_io(uint32_t io_index) ATTRIB_F1CODE;
uint32_t get_baud_config_for_io(uint32_t io_index) ATTRIB_F1CODE;
uint8_t set_baud_config_for_io(uint32_t io_index, uint32_t baud) ATTRIB_F1CODE;

uint8_t valid_io_pwm_freq(uint32_t pwm_freq_khz) ATTRIB_F1CODE;
uint32_t get_pwm_clock_divider(uint8_t pwm_freq_khz) ATTRIB_F1CODE;
uint8_t is_pwm_config_applicable_to_io(uint32_t io_index) ATTRIB_F1CODE;
uint8_t get_pwm_config_for_io(uint32_t io_index) ATTRIB_F1CODE;
uint8_t set_pwm_config_for_io(uint32_t io_index, uint8_t pwm_freq_khz) ATTRIB_F1CODE;

uint32_t get_spi_freq_from_clock_divider(uint32_t spi_clock_divider) ATTRIB_F1CODE;
uint32_t get_spi_clock_divider(uint8_t spi_freq_khz) ATTRIB_F1CODE;
uint8_t is_spi_config_applicable_to_io(uint32_t io_index) ATTRIB_F1CODE;
uint8_t get_spi_config_for_io(uint32_t io_index) ATTRIB_F1CODE;
uint8_t set_spi_config_for_standalone_spi_io(uint32_t io_index, uint8_t spi_freq_khz) ATTRIB_F1CODE;
uint8_t set_spi_config_for_io(uint32_t io_index, uint8_t spi_freq_khz) ATTRIB_F1CODE;
uint8_t valid_io_spi_freq(uint32_t spi_freq_khz) ATTRIB_F1CODE;
uint8_t configure_spi_out_for_shared_spi_config_hardware(uint16_t io_index, uint8_t spi_freq_khz) ATTRIB_F1CODE;
uint8_t configure_spi_in_for_shared_spi_config_hardware(uint16_t io_index, uint8_t spi_freq_khz) ATTRIB_F1CODE;

uint8_t get_software_interrupt_types_for_io(uint16_t io_index) ATTRIB_F1CODE;
e_status set_software_interrupt_types_for_io(uint16_t io_index, uint8_t interrupt_mask) ATTRIB_F1CODE;
e_status enable_software_interrupt_types_for_io(uint16_t io_index, uint8_t interrupt_mask) ATTRIB_F1CODE;
e_status disable_software_interrupt_types_for_io(uint16_t io_index, uint8_t interrupt_mask) ATTRIB_F1CODE;

volatile uint32_t get_software_interrupt_vector(void) ATTRIB_F1CODE;
volatile uint32_t get_software_interrupts_for_io(uint16_t io_index) ATTRIB_F1CODE;
e_status acknowledge_software_interrupts_for_io(uint16_t io_index, uint8_t interrupts) ATTRIB_F1CODE;

e_status set_io_type(uint16_t io_index, e_iotype io_type) ATTRIB_F1CODE;
e_status set_io_type_from_str(uint16_t io_index, char *io_type_str) ATTRIB_F1CODE;

e_status set_gpio(uint32_t user_io_num, uint32_t gpio_val) ATTRIB_F1CODE;
e_status get_gpio(uint32_t user_io_num, uint32_t *gpio_val) ATTRIB_F1CODE;

e_status set_pwm(uint32_t user_io_num, uint32_t pwm_val) ATTRIB_F1CODE;

e_status spi_tx_char(uint32_t user_io_num, char tx_char) ATTRIB_F1CODE;
e_status spi_tx_byte(uint32_t user_io_num, uint32_t tx_byte) ATTRIB_F1CODE;
e_status spi_tx_int(uint32_t user_io_num, uint32_t tx_word) ATTRIB_F1CODE;
e_status spi_rx_byte(uint32_t user_io_num, volatile uint8_t *rx_byte) ATTRIB_F1CODE;

e_status uart_tx_char(uint32_t user_io_num, char tx_char) ATTRIB_F1CODE;
e_status uart_tx_byte(uint32_t user_io_num, uint32_t tx_byte) ATTRIB_F1CODE;
e_status uart_tx_int(uint32_t user_io_num, uint32_t tx_word) ATTRIB_F1CODE;
e_status uart_rx_byte(uint32_t user_io_num, volatile uint8_t *uart_rx_val) ATTRIB_F1CODE;
e_status uart_rx_byte_nonblocking(uint32_t user_io_num, volatile uint8_t *uart_rx_val, uint8_t *uart_rx_val_valid) ATTRIB_F1CODE;

const char* standalone_io_type_tostring(e_iotype io_type) ATTRIB_F1CODE;
const char* relational_io_type_tostring(e_relational_iotype rel_io_type) ATTRIB_F1CODE;
const char* analog_io_type_tostring(e_analogtype analog_io_type) ATTRIB_F1CODE;

e_status reset_io_type_config(uint32_t io_index);
void reset_all_io_config(void);

void print_io_type_config(void);
void print_io_baud_config(void);
void print_io_pwm_config(void);
void print_io_spi_config(void);
void print_io_capabilities(void);
void save_io_config_as_start_on_boot(uint8_t print_progress);
void load_start_on_boot_config_for_all_io(void);

uint32_t get_default_spi_clock_divider(void);

#endif