#ifndef TD_MIMAS_A7_MINI
#ifndef TD_ARTY_S7
#ifndef TD_KV260

#ifndef MEMORY_GOWIN_H
#define MEMORY_GOWIN_H

#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <setjmp.h>
#include <locale.h>

#include "config.h"
#include "global.h"
#include "config.h"

// Functions

uint8_t initialise_memory(e_print_level print_level, uint8_t in_command_mode);
uint32_t get_memory_total_bytes(void);
uint32_t get_memory_free_bytes(void);

void free(void *ptr) ATTRIB_FASTESTCODE;
void *realloc(void *ptr, size_t size) ATTRIB_FASTESTCODE;
void *malloc(size_t size) ATTRIB_FASTESTCODE;
void *calloc(size_t nmemb, size_t size) ATTRIB_FASTESTCODE;

void *memcpy(void *dest, const void *src, size_t n) ATTRIB_FASTESTCODE;
volatile void *memcpy_volatile(volatile void *dest, const volatile void *src, size_t n) ATTRIB_FASTESTCODE;

void *memset(void *s, int c, size_t n) ATTRIB_FASTESTCODE;
volatile void *memset_volatile(volatile void *s, int c, size_t n) ATTRIB_FASTESTCODE;

int memcmp(const void *s1, const void *s2, size_t n) ATTRIB_FASTESTCODE;

uint8_t get_memory_usage_trace_enabled(void) ATTRIB_FASTESTCODE;
void enable_memory_usage_trace(void);
void disable_memory_usage_trace(void);

void reset_memory_free_bytes_min_observed(void) ATTRIB_FASTESTCODE;
uint32_t get_memory_free_bytes_min_observed(void) ATTRIB_FASTESTCODE;

void allow_only_fast_heap_large_regions(void) ATTRIB_FASTESTCODE;
void allow_all_fast_heap_regions(void) ATTRIB_FASTESTCODE;

void report_memory_layout(void);

void set_memory_alloc_size_occurances_track_accumulated(void);
void set_memory_alloc_size_occurances_track_nonaccumulated(void);
void print_memory_alloc_size_occurances(void);
void reset_memory_alloc_size_occurances(void) ATTRIB_FASTESTCODE;
void print_fast_memory_state(void);
void print_fast_memory_alloc_size_occurances(void);
void reset_fast_memory_alloc_size_occurances(void) ATTRIB_FASTESTCODE;

#endif

#endif
#endif
#endif
