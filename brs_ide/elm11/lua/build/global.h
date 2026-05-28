#ifndef globals_h
#define globals_h

#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>

#include "init.h"
#include "printf.h"
#include "ctype.h"

#include "config.h"


#if defined(TD_GW1NR_9_C6I5_S) || defined(TD_GW1NR_9_C7I6_B) || defined(TD_GW1NR_9_C7I6)
    #define FLASH_STORAGE_ENABLE
#endif

#define STR_DEVICE_NAME_CAPS                                    "EMBLUA"
#define STR_DEVICE_NAME                                         "embLua"
#define STR_DEVICE_NAME_CAMELCASE                               "embLua"
#define STR_DEVICE_DESCRIPTION                                  "the worlds most accessible physical computing device"

#define STR_CMD_UNSUPPORTED_FOR_STACK_SIZE_LESS_8K              "Command currently unsupported for stack size < 8192 bytes!"

#define C_COMMAND_MODE_SEPARATOR                                '|'
#define STR_COMMAND_MODE_SEPARATOR                              "|"

#define MAX_NUM_IO_PINS                                         (32)
#define MAX_NUM_ADC_PINS                                        (8)
#define MAX_NUM_DAC_PINS                                        (8)

#define NO_PRINT_PROGRESS                                       (0)
#define PRINT_PROGRESS                                          (1)

#define UNINTERRUPTIBLE_SLEEP                                   (0)
#define INTERRUPTIBLE_SLEEP                                     (1)
#define USER_CANCELLABLE_SLEEP                                  (2)
    // REVISIT: change to enum

#define USER_COMMS_RX_INTERRUPT_INTERRUPTIBLE_SLEEP_BITFLAG     (0x1)
#define IO_SOFTWARE_INTERRUPT_INTERRUPTIBLE_SLEEP_BITFLAG       (0x2)
#define SLEEP_IS_MICROSECONDS_BITFLAG                           (0x4)

#define SLEEP_REMAINING_TIMEOUT_BITFLAGS                        (0x03FF)
#define USER_EXIT_PROGRAM_INTERRUPT_BITFLAGS                    (0x6000)
    // NOTE: covers both individual and shared comms

#define COMMAND_MODE_DUMMY_ROWS_AT_TOP                          (2)
#define PRINT_CODE_MODE_MIN_CONSOLE_HEIGHT                      (20)

#define CORE_INFO_RD_INDEX                                      (14)
#define NUM_CORES_M1_SHIFT                                      (0)
#define NUM_CORES_M1_MASK                                       (0xF)
#define CORE_ID_SHIFT                                           (4)
#define CORE_ID_MASK                                            (0xF)

#define XBAR_LOCK_CFG_RD_INDEX                                  (14)
#define XBAR_LOCK_TX_CFG_SHIFT                                  (16)
#define XBAR_LOCK_TX_CFG_MASK                                   (0xFF)
#define XBAR_LOCK_RX_CFG_SHIFT                                  (24)
#define XBAR_LOCK_RX_CFG_MASK                                   (0xFF)

#define XBAR_LOCK_FIFO_TX_CFG_SHIFT                             (0)
#define XBAR_LOCK_FIFO_TX_CFG_MASK                              (0xFF)
#define XBAR_LOCK_FIFO_RX_CFG_SHIFT                             (8)
#define XBAR_LOCK_FIFO_RX_CFG_MASK                              (0xFF)

#define XBAR_DATA_CFG_RD_INDEX                                  (15)
#define XBAR_DATA_TX_CFG_SHIFT                                  (16)
#define XBAR_DATA_TX_CFG_MASK                                   (0xFF)
#define XBAR_DATA_RX_CFG_SHIFT                                  (24)
#define XBAR_DATA_RX_CFG_MASK                                   (0xFF)

#define XBAR_DATA_FIFO_TX_CFG_SHIFT                             (0)
#define XBAR_DATA_FIFO_TX_CFG_MASK                              (0xFF)
#define XBAR_DATA_FIFO_RX_CFG_SHIFT                             (8)
#define XBAR_DATA_FIFO_RX_CFG_MASK                              (0xFF)

#define CPU_FREQ_MHZ_RD_INDEX                                   (15)
#define CPU_FREQ_MHZ_MASK                                       (0xFFFF)

#define UART_CONFIG_RD_INDEX                                    (14)
#define UART_SHARED_COMMS_SHIFT                                 (8)
#define UART_SHARED_COMMS_MASK                                  (0x1)

#define TIMER_CONFIG_RD_INDEX                                   (14)
#define TIMER_ENABLE_SHIFT                                      (9)
#define TIMER_ENABLE_MASK                                       (0x1)

#define CLOCK_CONFIG_RD_INDEX                                   (14)
#define CLOCK_ENABLE_SHIFT                                      (10)
#define CLOCK_ENABLE_MASK                                       (0x1)

#define MEMORY_TRACE_CONFIG_RD_INDEX                            (14)
#define MEMORY_TRACE_ENABLE_SHIFT                               (11)
#define MEMORY_TRACE_ENABLE_MASK                                (0x1)

#define FPGA_IO_BUS_CONFIG_RD_INDEX                             (14)
#define FPGA_IO_BUS_ENABLE_SHIFT                                (12)
#define FPGA_IO_BUS_ENABLE_MASK                                 (0x1)

#define CPU_TRACE_CONFIG_RD_INDEX                               (14)
#define CPU_TRACE_ENABLE_SHIFT                                  (13)
#define CPU_TRACE_ENABLE_MASK                                   (0x1)

#define REBOOT_WAS_STACK_OVERFLOW_RD_INDEX                      (14)
#define REBOOT_WAS_STACK_OVERFLOW_SHIFT                         (14)
#define REBOOT_WAS_STACK_OVERFLOW_MASK                          (0x1)

#define CPU_CORE1_BITFLAG                                       (0x00000100)
#define CPU_CORE1_BITFLAG_SLR1                                  (CPU_CORE1_BITFLAG >> 1)
#define XBAR_TRANSACTION_NONBLOCKING                            (0x00010000)

#define IO_NUM_DIGITAL_PINS_SHIFT                               (0)
#define IO_NUM_DIGITAL_PINS_MASK                                (0x3F)
#define IO_NUM_ADC_SHIFT                                        (6)
#define IO_NUM_ADC_MASK                                         (0x1F)
#define IO_NUM_DAC_SHIFT                                        (11)
#define IO_NUM_DAC_MASK                                         (0x1F)
#define IO_ADC_PINS_ENABLED_SHIFT                               (16)
#define IO_ADC_PINS_ENABLED_MASK                                (0xFF)
#define IO_DAC_PINS_ENABLED_SHIFT                               (24)
#define IO_DAC_PINS_ENABLED_MASK                                (0xFF)

#define ANALOG_IO_ENABLED                                       (9)
#define ADC_ANALOG_BUFFER_CONFIG_RD_INDEX                       (10)
#define ADC_ANALOG_SW_INT_CONFIG_RD_INDEX                       (11)
#define DAC_ANALOG_BUFFER_CONFIG_RD_INDEX                       (12)
#define DAC_ANALOG_SW_INT_CONFIG_RD_INDEX                       (13)

#define ANALOG_IO_ENABLED_SHIFT                                 (0)
#define ANALOG_IO_ENABLED_BITMASK                               (0x1)
#define ANALOG_DAC_ENABLED_SHIFT                                (1)
#define ANALOG_DAC_ENABLED_BITMASK                              (0x1)
#define ANALOG_ADC_ENABLED_SHIFT                                (2)
#define ANALOG_ADC_ENABLED_BITMASK                              (0x1)

#define HEAP_SIZE_SHIFT                                         (8)
#define HEAP_SIZE_BITMASK                                       (0xFFFF)
#define STACK_SIZE_SHIFT                                        (24)
#define STACK_SIZE_BITMASK                                      (0xFF)

typedef struct {
    volatile uint32_t UNUSED_0;
    volatile uint32_t RXMODE_AND_CLKDIV_WO;

    volatile uint32_t DATA;
    volatile uint32_t UNUSED_1;

    volatile uint32_t DATA_BLOCKING;
} PICOUART;

typedef struct {
    // NOTE: registers are RW, unless otherwise
    // named.

    union {
        volatile uint32_t FIRMWARE_VERSION;
        volatile uint32_t FIRMWARE_VERSION_RD_INDEX_WO;
        volatile uint32_t ANALOG_CONFIG_RD_INDEX_WO;
        volatile uint32_t ANALOG_CONFIG_RO;
        volatile uint32_t CORE_INFO_RO;
        volatile uint32_t CORE_INFO_RD_INDEX_WO;
        volatile uint32_t UART_CONFIG_INDEX_WO;
        volatile uint32_t UART_CONFIG_RO;
        volatile uint32_t TIMER_CONFIG_INDEX_WO;
        volatile uint32_t TIMER_CONFIG_RO;
        volatile uint32_t CLOCK_CONFIG_INDEX_WO;
        volatile uint32_t CLOCK_CONFIG_RO;
        volatile uint32_t MEMORY_TRACE_CONFIG_INDEX_WO;
        volatile uint32_t MEMORY_TRACE_CONFIG_RO;
        volatile uint32_t FPGA_IO_BUS_CONFIG_INDEX_WO;
        volatile uint32_t FPGA_IO_BUS_CONFIG_RO;
        volatile uint32_t XBAR_LOCK_CFG_RO;
        volatile uint32_t XBAR_LOCK_CFG_RD_INDEX_WO;
        volatile uint32_t CPU_FREQ_MHZ_RO;
        volatile uint32_t CPU_FREQ_MHZ_RD_INDEX_WO;
        volatile uint32_t XBAR_DATA_CFG_RO;
        volatile uint32_t XBAR_DATA_CFG_RD_INDEX_WO;
        volatile uint32_t REBOOT_WAS_STACK_OVERFLOW_RD_INDEX_WO;
        volatile uint32_t REBOOT_WAS_STACK_OVERFLOW_RO;
    };

    volatile uint16_t TIMEOUT_COUNTER;
    volatile uint8_t TIMEOUT_COUNTER_INTERRUPTIBLE_WO;
    volatile uint8_t QSPI_DDR_CTRL;

    union {
        volatile uint32_t BOARD_LED_OUT_WO;
        volatile uint32_t IO_NUM_DIGITAL_PINS_RO;
        volatile uint32_t IO_NUM_ADC_RO;
        volatile uint32_t IO_NUM_DAC_RO;
        volatile uint32_t BOARD_BOOT_STATE_RW;
    };

    union {
        volatile uint32_t SYSTEM_TIMER_CTRL_WO;
        volatile uint32_t SYSTEM_TIMER_DATA_RO;
    };
    union {
        volatile uint32_t SYSTEM_TIMER_CACHE_CTRL_WO;
        volatile uint32_t SYSTEM_TIMER_CACHE1_DATA_RO;
    };
    volatile uint32_t SYSTEM_TIMER_CACHE2_DATA_RO;

    volatile uint32_t IO_TARGET_INDEX_WO;
    volatile uint32_t IO_BUILD_CONFIG_RO;
    volatile uint32_t IO_FUNCTION_WO;
    union {
        volatile uint32_t IO_PWM_CLOCK_DIVIDER_WO;
        volatile uint32_t IO_SPI_CLOCK_DIVIDER_WO;
        volatile uint32_t IO_UART_CLOCK_DIVIDER_WO;
    };
    volatile uint32_t IO_DATA_TX_WO;
    volatile uint32_t IO_DATA_RX_RO;

    volatile uint16_t IO_SOFTWARE_GLOBAL_INTERRUPT_ENABLE_WO;
    volatile uint16_t IO_SOFTWARE_INTERRUPT_MASK_WO;
    volatile uint32_t IO_SOFTWARE_INTERRUPT_RO;
    volatile uint32_t IO_SOFTWARE_INTERRUPT_VECTOR;

    union {
        volatile uint16_t USER_COMMS_RX_ESC_SEQ_FILTER_DISABLE_WO;
        volatile uint16_t USER_SHARED_COMMS_RX_INTERRUPT_MODE_ENABLE_WO;

        volatile uint16_t XBAR_LOCK_FIFO_CFG_RO;
    };
    union {
        volatile uint16_t XBAR_FIFO_CFG_RD_INDEX_WO;
        volatile uint16_t XBAR_DATA_FIFO_CFG_RO;
    };

    volatile uint32_t SHARED_SPI_BUILD_CONFIG_RO;
    volatile uint32_t SHARED_SPI_TARGET_INDEX_WO;
    volatile uint32_t SHARED_SPI_DATA_TX_WO;
    volatile uint32_t SHARED_SPI_DATA_RX_RO;
    volatile uint32_t SHARED_SPI_ENABLE_WO;
    volatile uint32_t SHARED_SPI_CLOCK_DIVIDER_WO;
    volatile uint32_t SHARED_SPI_MAPPING_WO;

    union {
        volatile uint32_t MEM_INFO_REG_RD_INDEX_WO;
        volatile uint32_t HEAP_AND_STACK_COUNT_RO;
        volatile uint32_t HEAP_MEMORY_LOW_WARNING_FLAGS_RO;
        volatile uint32_t HEAP_MEMORY_FREE_RO;
        volatile uint32_t HEAP_MEMORY_LOW_WATER_MARK_RO;
        volatile uint32_t HEAP_OUT_OF_MEMORY_WO;
        volatile uint32_t STACK_OVERFLOW_TRACE_ENABLE_WO;
        volatile uint32_t STACK_OVERFLOW_OCCURRED_WO;
        volatile uint32_t STACK_MEMORY_HIGH_WATER_MARK_RESET_WO;
        volatile uint32_t STACK_MEMORY_HIGH_WATER_MARK_RO;
        volatile uint32_t CPU_ADDR_ACCESS_LOW_WATER_MARK_RO;
        volatile uint32_t CPU_ADDR_ACCESS_HIGH_WATER_MARK_RO;
    };

    volatile uint32_t UART_SHARED_COMMS;

/*
    volatile uint32_t ANALOG_SPI_WO;
    volatile uint32_t ANALOG_ADC_AUTOSCAN_ENABLE_WO;
    union {
        volatile uint32_t ANALOG_ADC_AUTOSCAN_CHANNEL_READ_INDEX_WO;
        volatile uint32_t ANALOG_ADC_AUTOSCAN_DATA_RO;
    };
*/

    volatile uint32_t XBAR_LOCK_WO;
    volatile uint32_t XBAR_LOCK_RO;

    volatile uint32_t XBAR_DATA_WO;
    volatile uint32_t XBAR_DATA_RO;

    union {
        volatile uint32_t HARDWARE_WATCHDOG_RESET_WO;
        volatile uint32_t HARDWARE_WATCHDOG_TIMER_MS_RO;
        volatile uint32_t COMPATIBLE_HARDWARE_ID_RO;
    };
    union {
        volatile uint32_t HARDWARE_ID_RO;
        volatile uint32_t HARDWARE_WATCHDOG_TIMEOUT_MS_RO;
    };

    union {
        volatile uint32_t LVM_EXEC_WO;
        volatile uint32_t USER_COMMS_RX_INTERRUPT_RO;
        volatile uint32_t USER_BUTTON_RO;
        volatile uint32_t USER_EXIT_PROGRAM_INTERRUPT_RO;
    };


    // NOTE: dummy entries so code compiles!!!
    volatile uint32_t ANALOG_SPI_WO;
    volatile uint32_t ANALOG_ADC_AUTOSCAN_ENABLE_WO;
    union {
        volatile uint32_t ANALOG_ADC_AUTOSCAN_CHANNEL_READ_INDEX_WO;
        volatile uint32_t ANALOG_ADC_AUTOSCAN_DATA_RO;
    };

} UTILS;

typedef enum {
    e_cpu_prompt_unconfigured   = 0,
    e_no_cpu_prompt,
    e_core_num,
    e_num_cpu_prompt_types
} e_cpu_prompt_format;

typedef enum {
    e_time_prompt_unconfigured  = 0,
    e_no_time_prompt,
    e_system_clock,
    e_load_and_call_duration,
    e_call_duration,
    e_load_duration,
    e_num_time_prompt_types
} e_time_prompt_format;

typedef enum e_led_st
{
    e_off               = 0,
    e_on,
    e_total_led_states
} e_led_st;
    // NOTE: st == state

typedef enum e_board_led
{
    e_led1               = 0,
    e_led2,
    e_led3,
    e_led4,
    e_led5,
    e_total_board_leds
} e_board_led;
    // NOTE: st == state

typedef enum e_print_level
{
    e_print_none        = 0,
    e_print_verbose,
    e_print_progress,
    e_total_print_levels
} e_print_level;

typedef enum {
    e_system_time_cache1        = 0,
    e_system_time_cache2,
    e_num_system_time_caches
} e_system_time_cache;

typedef enum e_global_interrupt_st
{
    e_software_interrupts_disabled      = 0,
    e_software_interrupts_enabled,
    e_total_global_interrupt_states
} e_global_interrupt_st;
    // NOTE: st == state

typedef enum e_global_repl_interrupt_mode
{
    e_repl_interrupt_mode_disabled  = 0,
    e_repl_interrupt_mode_enabled
} e_global_repl_interrupt_mode;

typedef enum e_sleep_end_cause
{
    e_sleep_completed  = 0,
    e_user_cancelled,
    e_interrupted
} e_sleep_end_cause;

typedef enum e_cores
{
    e_core_none = 0,
    e_core1,
    e_core2,
    e_core3,
    e_core4,
    e_core5,
    e_core6,
    e_core7,
    e_core8
} e_cores;

#define XSTR(s) STR(s)
#define STR(s) #s

#ifndef VERSION
    #define SOFTWARE_VERSION "Undefined!"
#else
    #define SOFTWARE_VERSION XSTR(VERSION)
#endif

#ifndef TD_GW1NR_9_C6I5_S
    // NOTE: TD == Target Device

    #ifndef TD_GW1NR_9_C7I6
        #ifndef TD_GW1NR_9_C7I6_B
            #ifndef TD_KV260
                #ifndef TD_ARTY_S7
                    #ifndef TD_MIMAS_A7_MINI
                        #error "Unknown TARGET DEVICE !"
                    #endif
                #endif
            #endif
        #endif
    #endif
#endif

// TODO: just have this in one place... memory_map.h in
// 'shared' directory or something...
#ifdef TD_MIMAS_A7_MINI
    #define SPI_XIP_BASE_ADDR       (0x10000000)
    #define SPI_CFG_BASE_ADDR       (0x20000000)
    #define IO_UTILS_BASE_ADDR      (0x40000000)
    #define USER_COMMS_BASE_ADDR    (0x70000000)
    #define SRAM_BASE_ADDR          (0x80000000)
#endif

#ifdef TD_ARTY_S7
    #define SPI_XIP_BASE_ADDR       (0x10000000)
    #define FPGA_BUS_BASE_ADDR      (0x20000000)
    #define IO_UTILS_BASE_ADDR      (0x40000000)
    #define USER_COMMS_BASE_ADDR    (0x70000000)

    #define SRAM_BASE_ADDR          (0x80000000)
    #define HEAP1_BASE_ADDR         (SRAM_BASE_ADDR + 0x20000000)
    #define HEAP2_BASE_ADDR         (SRAM_BASE_ADDR + 0x10000000)
    #define HEAP3_BASE_ADDR         (SRAM_BASE_ADDR + 0x08000000)
        // NOTE: cannot have bit-flag < than 0xFF000000

    #define MMAP_BASE_ADDR          (0x80000000)
    #define MMAP1_BASE_ADDR         (MMAP_BASE_ADDR + 0x00800000)
    #define MMAP2_BASE_ADDR         (MMAP_BASE_ADDR + 0x00400000)
    #define MMAP3_BASE_ADDR         (MMAP_BASE_ADDR + 0x00200000)
#endif

#ifdef TD_KV260
    #define IO_UTILS_BASE_ADDR      (0x40000000)
    #define USER_COMMS_BASE_ADDR    (0x60000000)
    #define SRAM_BASE_ADDR          (0x80000000)
#endif

#ifdef TD_GW1NR_9_C6I5_S
    #define SPI_XIP_BASE_ADDR       (0x00000000)
    #define SPI_CFG_BASE_ADDR       (0x20000000)
    #define IO_UTILS_BASE_ADDR      (0x40000000)
    #define FPGA_BUS_BASE_ADDR      (0x60000000)
    #define BROM_BASE_ADDR          (0x60000000)
        // NOTE: same address as 'FPGA_BUS_BASE_ADDR' - check RTL
        // and hardware compilation configuration to determine which
        // is being addressed.
    #define USER_COMMS_BASE_ADDR    (0x70000000)
    #define LVM_ADDR                (0x78000000)

    #define SRAM_BASE_ADDR          (0x80000000)
    #define HEAP1_BASE_ADDR         (SRAM_BASE_ADDR + 0x20000000)
    #define HEAP2_BASE_ADDR         (SRAM_BASE_ADDR + 0x10000000)
    #define HEAP3_BASE_ADDR         (SRAM_BASE_ADDR + 0x08000000)

    #define MMAP_BASE_ADDR          (0x80000000)
    #define MMAP1_BASE_ADDR         (MMAP_BASE_ADDR + 0x00800000)
    #define MMAP2_BASE_ADDR         (MMAP_BASE_ADDR + 0x00400000)
    #define MMAP3_BASE_ADDR         (MMAP_BASE_ADDR + 0x00200000)
#endif

#ifdef TD_GW1NR_9_C7I6_B
    #define SPI_XIP_BASE_ADDR       (0x00000000)
    #define SPI_CFG_BASE_ADDR       (0x20000000)
    #define IO_UTILS_BASE_ADDR      (0x40000000)
    #define FPGA_BUS_BASE_ADDR      (0x60000000)
    #define BROM_BASE_ADDR          (0x60000000)
        // NOTE: same address as 'FPGA_BUS_BASE_ADDR' - check RTL
        // and hardware compilation configuration to determine which
        // is being addressed.
    #define USER_COMMS_BASE_ADDR    (0x70000000)
    #define LVM_ADDR                (0x78000000)

    #define SRAM_BASE_ADDR          (0x80000000)
    #define HEAP1_BASE_ADDR         (SRAM_BASE_ADDR + 0x20000000)
    #define HEAP2_BASE_ADDR         (SRAM_BASE_ADDR + 0x10000000)
    #define HEAP3_BASE_ADDR         (SRAM_BASE_ADDR + 0x08000000)

    #define MMAP_BASE_ADDR          (0x80000000)
    #define MMAP1_BASE_ADDR         (MMAP_BASE_ADDR + 0x00800000)
    #define MMAP2_BASE_ADDR         (MMAP_BASE_ADDR + 0x00400000)
    #define MMAP3_BASE_ADDR         (MMAP_BASE_ADDR + 0x00200000)
#endif

#ifdef TD_GW1NR_9_C7I6
    #define SPI_XIP_BASE_ADDR       (0x00000000)
    #define SPI_CFG_BASE_ADDR       (0x20000000)
    #define IO_UTILS_BASE_ADDR      (0x40000000)
    #define BROM_BASE_ADDR          (0x60000000)
    #define FPGA_BUS_BASE_ADDR      (0x68000000)
    #define USER_COMMS_BASE_ADDR    (0x70000000)
    #define LVM_ADDR                (0x78000000)

    #define SRAM_BASE_ADDR          (0x80000000)
    #define HEAP1_BASE_ADDR         (SRAM_BASE_ADDR + 0x20000000)
    #define HEAP2_BASE_ADDR         (SRAM_BASE_ADDR + 0x10000000)
    #define HEAP3_BASE_ADDR         (SRAM_BASE_ADDR + 0x08000000)

    #define MMAP_BASE_ADDR          (0x80000000)
    #define MMAP1_BASE_ADDR         (MMAP_BASE_ADDR + 0x00800000)
    #define MMAP2_BASE_ADDR         (MMAP_BASE_ADDR + 0x00400000)
    #define MMAP3_BASE_ADDR         (MMAP_BASE_ADDR + 0x00200000)
#endif

#define NOOP                                                    (void)0

#define UTILS0                                                  ((volatile UTILS *)IO_UTILS_BASE_ADDR)

#define UART0                                                   ((volatile PICOUART *)USER_COMMS_BASE_ADDR)

#define FPGA_BUS0                                               ((volatile uint32_t *)FPGA_BUS_BASE_ADDR)
#define FPGA_BUS_NONBLOCKING_FLAG                               (0x01000000)
#define FPGA_BUS_READ_PREVIOUS_TRANSACTION_RESULT_FLAG          (0x02000000)

#define LVM                                                     ((volatile uint32_t *)LVM_ADDR)

#define SYSTEM_TIMER_CTRL_LOCK_BITFLAG                          (0x01)
#define SYSTEM_TIMER_CTRL_RD_MILLISECONDS_BITFLAG               (0x02)

#define SYSTEM_TIMER_CACHE_CTRL_TRIG_CACHING_CACHE1_BITFLAG     (0x01)
#define SYSTEM_TIMER_CACHE_CTRL_TRIG_CACHING_CACHE2_BITFLAG     (0x02)
#define SYSTEM_TIMER_CACHE_CTRL_CLEAR_CACHES_BITFLAG            (0x04)
#define SYSTEM_TIMER_CACHE_CTRL_RD_MILLISECONDS_BITFLAG         (0x08)

#define STACK_HIGH_WATER_MARK_TRACE_RESET_BITFLAG               (0x10000000)
#define HEAP_OUT_OF_MEMORY_BITFLAG                              (0x20000000)
#define STACK_OVERFLOW_OCCURRED_RESET_BITFLAG                   (0x40000000)
#define STACK_OVERFLOW_TRACE_ENABLE_BITFLAG                     (0x80000000)

#define SPI_CLK_DIVIDER_FREQ_HZ                                 (1000000)

#define USER_EXIT_PROGRAM_INTERRUPT_MASK                        (0x00000006)

#define QSPI_IN_CFG_MODE_FLAG                                   (0x20)

#define ANSI_COLOR_RED                                          "\x1b[31m"
#define ANSI_COLOR_GREEN                                        "\x1b[32m"
#define ANSI_COLOR_YELLOW                                       "\x1b[33m"
#define ANSI_COLOR_BLUE                                         "\x1b[34m"
#define ANSI_COLOR_MAGENTA                                      "\x1b[35m"
#define ANSI_COLOR_CYAN                                         "\x1b[36m"
#define ANSI_COLOR_WHITE                                        "\x1b[37m"
#define ANSI_COLOR_BRIGHT_RED                                   "\x1b[91m"
#define ANSI_COLOR_RESET                                        "\x1b[0m"

#define ANSI_COLOR_REPL_YELLOW                                  "\x1b[38;5;222m"
#define ANSI_COLOR_GRAY                                         "\x1b[38;5;252m"

#define ANSI_COLOR_CORE1                                        "\x1b[38;5;159m"
#define ANSI_COLOR_CORE2                                        "\x1b[38;5;157m"
#define ANSI_COLOR_CORE3                                        "\x1b[38;5;155m"
#define ANSI_COLOR_CORE4                                        "\x1b[38;5;148m"
#define ANSI_COLOR_CORE5                                        "\x1b[38;5;150m"
#define ANSI_COLOR_CORE6                                        "\x1b[38;5;152m"
#define ANSI_COLOR_CORE7                                        "\x1b[38;5;147m"
#define ANSI_COLOR_CORE8                                        "\x1b[38;5;144m"

#define ANSI_COLOR_LIGHT_BLUE                                   "\x1b[38;5;75m"
#define ANSI_COLOR_LIGHT_CYAN                                   "\x1b[38;5;66m"

#define ANSI_BACKGROUND_COLOR_DARK                              "\x1b[48;5;232m"

#define REPL_MODE                                               (0)
#define COMMAND_MODE                                            (1)



uint8_t user_exit_program_interrupt() ATTRIB_RUNTIMECODE;

#ifdef DEBUG_VPRINT_CPU_ACCESS
    uint32_t get_cpu_addr_access_low_water_mark(void) ATTRIB_RUNTIMECODE;
    uint32_t get_cpu_addr_access_high_water_mark(void) ATTRIB_RUNTIMECODE;
    uint8_t print_cpu_access_trace(void) ATTRIB_RUNTIMECODE;
#else
    uint32_t get_cpu_addr_access_low_water_mark(void);
    uint32_t get_cpu_addr_access_high_water_mark(void);
    uint8_t print_cpu_access_trace(void);
#endif


void init_globals(void);

void read_cpu_freq(void);
void read_core_info(void);

uint8_t get_num_cores(void);
uint8_t get_core_id(void);

uint32_t get_cpu_freq_hz(void);
uint32_t get_cpu_freq_khz(void);
uint32_t get_cpu_freq_mhz(void);

uint8_t was_reboot_due_to_stack_overflow(void);

void read_uart_cfg(void);
void uart_init(void);
void user_comms_enable_rx_interrupt_mode(void);
void user_comms_disable_rx_interrupt_mode(void);
uint8_t uart_read_char();
uint8_t uart_read_char_blocking();
char uart_read_char_maxwait_ms(uint16_t ms);
void uart_write_char(int c);
void uart_write_string(const char *p);
void uart_write_hexidecimal(uint32_t v, int digits);
void uart_write_ptr_hexidecimal(void *v, int digits);
void uart_write_uint32_t(uint32_t v);
void uart_write_float(float f);
void uart_write_string_with_prompts(e_cpu_prompt_format pf_cpu, e_time_prompt_format pf_time, const char *str,
                                        uint8_t in_command_mode);

void delay_milliseconds(uint16_t milliseconds);

uint8_t get_uart_cfg(void);

uint32_t get_xbar_lock_cfg(void);
uint32_t get_xbar_lock_tx_fifo_depth(uint32_t core_id);
uint32_t get_xbar_unlock_cfg(void);
uint32_t get_xbar_lock_rx_fifo_depth(uint32_t core_id);
uint32_t get_xbar_data_tx_cfg(void);
uint32_t get_xbar_data_tx_fifo_depth(uint32_t core_id);
uint32_t get_xbar_data_rx_cfg(void);
uint32_t get_xbar_data_rx_fifo_depth(uint32_t core_id);


uint8_t xbar_lock(uint8_t core);
uint8_t xbar_lock_nonblocking(uint8_t core, uint8_t *success);
uint8_t xbar_unlock(uint8_t core);
uint8_t xbar_unlock_nonblocking(uint8_t core, uint8_t *success);

uint8_t xbar_data_tx(uint8_t core, uint8_t byte);
uint8_t xbar_data_tx_nonblocking(uint8_t core, uint8_t byte, uint8_t *success);
uint8_t xbar_data_rx(uint8_t core, uint8_t *byte);
uint8_t xbar_data_rx_nonblocking(uint8_t core, uint8_t *byte, uint8_t *success);

void init_cpu_prompt_format_for_repl(void);
void increment_cpu_prompt_format(void);

e_time_prompt_format get_time_prompt_format(void);
e_cpu_prompt_format get_cpu_prompt_format(void);
void set_time_prompt_format(e_time_prompt_format pf);
void set_cpu_prompt_format(e_cpu_prompt_format cpu_prompt_format);
void increment_time_prompt_format(void);
uint8_t is_valid_time_prompt_format(e_time_prompt_format pf);
const char* time_prompt_format_to_string(e_time_prompt_format pf);
const char* cpu_prompt_format_to_string(e_cpu_prompt_format pf);

void read_performance_timer_cfg(void);
uint8_t get_performance_timer_cfg(void);
void clear_system_time_caches(void) ATTRIB_F1CODE;
void trigger_caching_of_system_time(e_system_time_cache cache) ATTRIB_F1CODE;

void read_general_timer_cfg(void);
uint8_t get_general_timer_cfg(void);
void cancel_interruptible_sleep(void);
uint8_t doing_interruptible_sleep(void);
e_sleep_end_cause sleep_milliseconds(uint16_t ms, uint8_t interruptible_options) ATTRIB_F1CODE;
e_sleep_end_cause continue_sleep_milliseconds(uint8_t interruptible_options) ATTRIB_F1CODE;
e_sleep_end_cause sleep_microseconds(uint16_t microsec, uint8_t interruptible_options) ATTRIB_F1CODE;
e_sleep_end_cause continue_sleep_microseconds(uint8_t interruptible_options) ATTRIB_F1CODE;

uint8_t set_board_leds_state(const e_led_st *led_st, uint8_t num_leds);
uint8_t set_board_led_state(e_board_led board_led, e_led_st led_st);
uint8_t get_board_led_state(e_board_led board_led);
uint8_t toggle_board_led_state(e_board_led board_led);
uint8_t set_all_board_leds_off(void);
uint8_t set_board_leds_hw_mode(void);
uint8_t set_board_leds_sw_mode(void);

void set_software_interrupt_enabled_state(e_global_interrupt_st state) ATTRIB_F1CODE;
uint8_t software_interrupts_enabled(void) ATTRIB_F1CODE;

void set_repl_interrupt_mode(e_global_repl_interrupt_mode state) ATTRIB_F1CODE;
uint8_t repl_interrupt_mode_enabled(void) ATTRIB_F1CODE;

void remove_trailing_nl_and_cr(char *str);

void set_successfully_booted_hardware_flag(void);
uint8_t get_successfully_booted_hardware_flag(void);
uint8_t valid_hardware_id(void);
void reboot_board(void);
char *get_firmware_version(void);
char *get_hardware_id(void);

uint32_t get_hardware_watchdog_timer_ms(void);
uint32_t get_hardware_watchdog_timeout_ms(void);
void reset_hardware_watchdog_ms(void);

uint32_t get_memory_trace_enabled(void);

uint32_t read_fpga_io_bus_enabled(void);

uint32_t get_stack_memory_total_kb(void);
uint32_t get_stack_low_water_mark(void);
void reset_stack_low_water_mark(void);
void enable_stack_overflow_trace(void);
void reset_stack_overflow_occurred_flag(void);
void set_out_of_heap_memory_flag(void);

uint32_t get_heap_memory_total_kb(void);
uint32_t get_heap_memory_free(void);
uint32_t get_heap_memory_free_low_water_mark(void);
void reset_heap_low_water_mark(void);

uint8_t fgets_with_history(uint8_t in_command_mode, const char *prmt, char *buffer, size_t size,
                                char **history_line_buffer, uint8_t history_wr_index,
                                    uint8_t max_history_lines);

uint8_t get_cursor_position(uint16_t *row, uint16_t *col);
uint8_t get_console_rows_with_default_on_failure(uint16_t *console_rows);
uint8_t get_console_cols_with_default_on_failure(uint16_t *cursor_cols);
uint8_t clear_console_and_history_and_reset_cursor(void);
uint8_t move_cursor_to_top_of_screen(void);
uint8_t move_cursor_to_bottom_of_screen(void);

void print_full_page_print_footer(const char *page_type, const char *page_name, uint16_t total_lines, uint16_t curr_line);

uint8_t user_button_is_pressed(void) __attribute__ ((unused));

void disable_user_comms_rx_esc_seq_filter(void);
void enable_user_comms_rx_esc_seq_filter(void);

void set_color_for_repl_mode(void);
void set_color_for_command_mode(void);
void set_color_for_command_mode_bright(void);
void set_color_for_command_mode_category(void);
void set_color_for_command_mode_error(void);
void set_color_for_command_mode_command(void);
void set_color_for_command_mode_highlighting(void);

#endif
