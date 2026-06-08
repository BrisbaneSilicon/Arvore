#ifndef FLASH_H
#define FLASH_H

#include "global.h"
#include "config.h"
#include "precompiler_macros.h"

#include "config.h"


// ---------------------- Defines ----------------------

#define FLASH_MAX_CORES_SUPPORTED                   (2)

#define FLASH_PAGE_BYTES                            (256)

#define MAX_NUM_PROGRAMS                            (128)
#define MAX_FLASH_PAGES_PER_PROGRAM                 (96)
#define MAX_BYTES_PER_PROGRAM                       (FLASH_PAGE_BYTES * MAX_FLASH_PAGES_PER_PROGRAM)-1
    // NOTE: -1 for required NULL delimiter
    //
    // 24576 bytes / program... at 128 programs
    // max, ends up being 3 MB total...

// NOTE: addresses of data in flash
#define PIN_CONFIG_START_ADDR                       (0x00)
#define PIN_CONFIG_END_ADDR                         ((PIN_CONFIG_START_ADDR + MAX_NUM_IO_PINS) - 1)
    // REVISIT: for now, waste one page per I/O
    // pin...

#define STORAGE_METADATA_ADDR                       (PIN_CONFIG_END_ADDR+1)

#define PROGRAM_ENTRY_TABLE_START_ADDR              (STORAGE_METADATA_ADDR+1)
#define PROGRAM_ENTRY_TABLE_END_ADDR                (PROGRAM_ENTRY_TABLE_START_ADDR + (MAX_NUM_PROGRAMS/PROGRAM_ENTRY_TABLE_ENTRIES_PER_FLASH_PAGE))
    // REVISIT: for now, potentially waste one
    // page here...

#define PROGRAM_DATA_START_ADDR                     (PROGRAM_ENTRY_TABLE_END_ADDR+1)
#define PROGRAM_DATA_INC_ADDR                       (MAX_FLASH_PAGES_PER_PROGRAM)


#define PROG_ENTRY_NAME_MAX_CHARS                   (29)
    // NOTE: sized so 'PROG_ENTRY_NAME_MAX_CHARS'
    // plus 1 plus sizeof(uint16_t) == 32
    // characters, which will fit evenly into
    // 'FLASH_PAGE_BYTES'...
#define PROG_ENTRY_NAME_MAX_CHARS_PLUS_NTC          (PROG_ENTRY_NAME_MAX_CHARS + 1)
    // NOTE: NTC == Null Terminating Character
#define PROGRAM_NAME_MAX_CHARS                      (32)

#define PROGRAM_ENTRY_TABLE_ENTRIES_PER_FLASH_PAGE  (FLASH_PAGE_BYTES/sizeof(st_prog_entry))


typedef struct {
    union {
        volatile uint32_t REG;
        volatile uint16_t IOW;
        struct {
            volatile uint8_t IO;
            volatile uint8_t OE;
            volatile uint8_t CFG;
            volatile uint8_t EN;
        };
    };
} PICOQSPI;

typedef struct {
    volatile uint8_t instr;
    volatile uint8_t addr[3];
        // NOTE: in transmit sequence:
        //  addr[0] -> 23:16
        //  addr[1] -> 15:8
        //  addr[2] -> 7:0

    volatile uint8_t data_buf[FLASH_PAGE_BYTES];
} st_flash_idbuf;
    // NOTE: i == instruction
    // NOTE: d == data

typedef struct {
    volatile uint8_t instr;
    volatile uint8_t addr[3];
        // NOTE: in transmit sequence:
        //  addr[0] -> 23:16
        //  addr[1] -> 15:8
        //  addr[2] -> 7:0
} st_flash_ibuf;
    // NOTE: i == instruction

typedef struct {
    char prog_name[PROG_ENTRY_NAME_MAX_CHARS_PLUS_NTC];
    uint16_t prog_data_start_addr;
} st_prog_entry;

typedef struct {
    st_prog_entry prog_entry[FLASH_PAGE_BYTES/sizeof(st_prog_entry)];
} st_flash_page_prog_entries;

typedef struct {
    uint32_t total_programs;
    uint8_t program_data_slot_used[MAX_NUM_PROGRAMS/8];
        // NOTE: idea here is that at _some_ point, programs
        // might start utilising more than one data slot
    char program_start_on_boot[FLASH_MAX_CORES_SUPPORTED][PROG_ENTRY_NAME_MAX_CHARS_PLUS_NTC];
    uint8_t time_prompt_format[FLASH_MAX_CORES_SUPPORTED];
    uint8_t cpu_prompt_format[FLASH_MAX_CORES_SUPPORTED];
} st_storage_metadata;
    // NOTE: currently, size cannot exceed a page of
    // flash memory...

assert_defined_type_size_equal_or_less_than( st_storage_metadata, FLASH_PAGE_BYTES );


#define BOARD_ID_BYTES      (3)

#define FLASHIO_REQWREN     (0x01)

#define QSPI_IO_CSB         (0x20)
#define QSPI_IO_CLK         (0x10)
#define QSPI_IO_MOSI        (0x01)
#define QSPI_IO_MISO        (0x02)
#define QSPI_OE_MOSI        (0x0100)
#define QSPI_EN_ENABLE      (0x80)

#define QSPI_FLASH_SE       (0x20)
#define QSPI_FLASH_PE       (0x81)
#define QSPI_FLASH_PP       (0x02)
#define QSPI_FLASH_READ     (0x03)
#define QSPI_FLASH_RDSR     (0x05)
#define QSPI_FLASH_WREN     (0x06)
#define QSPI_FLASH_SE       (0x20)
#define QSPI_FLASH_PP       (0x02)
#define QSPI_FLASHSR_WIP    (0x01)

#define QSPI_REG_CRM        (0x00100000)
#define QSPI_REG_DSPI       (0x00400000)

#define QSPI0               ((volatile PICOQSPI*)SPI_CFG_BASE_ADDR)


// --------------- Function Prototypes ----------------

void spi_flashio(volatile uint8_t *pdata, int length, int wren) ATTRIB_RUNTIMECODE_FLASHIO;
void spi_flashio_wrapper(volatile uint8_t *pdata, int length, int wren) ATTRIB_F1CODE_BUILDSWITCH;
void init_flash(void) ATTRIB_F1CODE_BUILDSWITCH;

uint8_t read_board_id(uint8_t *board_id) ATTRIB_F1CODE_BUILDSWITCH;

uint8_t read_flash_page_byte(uint16_t page_addr, volatile uint8_t *page_byte) ATTRIB_F1CODE_BUILDSWITCH;
uint8_t read_flash_page(uint16_t page_addr, volatile uint8_t *page_data) ATTRIB_F1CODE_BUILDSWITCH;
uint8_t write_flash_page(uint16_t page_addr, volatile uint8_t *page_data) ATTRIB_F1CODE_BUILDSWITCH;

uint8_t write_io_type_to_flash(uint8_t io_index, uint8_t io_config) ATTRIB_F1CODE_BUILDSWITCH;
uint8_t read_io_type_from_flash(uint8_t io_index) ATTRIB_F1CODE_BUILDSWITCH;
uint8_t write_adc_enabled_state_to_flash(uint8_t adc_index, uint8_t adc_enabled) ATTRIB_F1CODE_BUILDSWITCH;
uint8_t read_adc_config_state_from_flash(uint8_t adc_index) ATTRIB_F1CODE_BUILDSWITCH;
uint8_t write_dac_enabled_state_to_flash(uint8_t dac_index, uint8_t dac_enabled) ATTRIB_F1CODE_BUILDSWITCH;
uint8_t read_dac_config_state_from_flash(uint8_t dac_index) ATTRIB_F1CODE_BUILDSWITCH;

uint8_t initialise_storage_metadata(void) ATTRIB_F1CODE_BUILDSWITCH;
uint8_t reset_program_name_start_on_boot(void) ATTRIB_F1CODE_BUILDSWITCH;
uint8_t set_program_name_start_on_boot(const char *prog_name) ATTRIB_F1CODE_BUILDSWITCH;
volatile const char* get_program_name_start_on_boot(void) ATTRIB_F1CODE_BUILDSWITCH;
uint8_t is_program_start_on_boot_valid(void) ATTRIB_F1CODE_BUILDSWITCH;
uint8_t clear_storage_metadata_slot_for_addr(uint16_t prog_addr) ATTRIB_F1CODE_BUILDSWITCH;
uint8_t set_storage_metadata_slot_for_addr(uint16_t prog_addr) ATTRIB_F1CODE_BUILDSWITCH;

uint8_t set_prompt_formats_start_on_boot(e_time_prompt_format time_prompt_format, e_cpu_prompt_format cpu_prompt_format) ATTRIB_F1CODE_BUILDSWITCH;
e_time_prompt_format get_time_prompt_format_start_on_boot(void) ATTRIB_F1CODE_BUILDSWITCH;
e_cpu_prompt_format get_cpu_prompt_format_start_on_boot(void) ATTRIB_F1CODE_BUILDSWITCH;

uint8_t make_new_program_entry(char *prog_name, uint16_t *prog_addr) ATTRIB_F1CODE_BUILDSWITCH;
uint8_t get_start_addr_of_program(const char *prog_name, uint16_t *prog_addr) ATTRIB_F1CODE_BUILDSWITCH;
uint16_t read_program_pages(uint8_t num_pages, uint16_t page_start_addr, volatile uint8_t *buffer, volatile uint8_t *last_page) ATTRIB_F1CODE_BUILDSWITCH;
uint8_t upload_program(char *prog_name) ATTRIB_F1CODE_BUILDSWITCH;
uint8_t delete_program(char *prog_name) ATTRIB_F1CODE_BUILDSWITCH;
uint8_t delete_all_programs(e_print_level print_lvl) ATTRIB_F1CODE_BUILDSWITCH;

void print_all_program_names(void) ATTRIB_F1CODE_BUILDSWITCH;
void print_all_program_addrs(void) ATTRIB_F1CODE_BUILDSWITCH;

uint8_t print_num_saved_programs(void) ATTRIB_F1CODE_BUILDSWITCH;
uint8_t print_program_data_slot_utilisation(void) ATTRIB_F1CODE_BUILDSWITCH;

#endif