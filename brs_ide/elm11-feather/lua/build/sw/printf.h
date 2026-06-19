#ifndef PRINTF_H
#define PRINTF_H

#include <stdarg.h>
#include <stddef.h>

#include "config.h"

// ---------------------- Defines ----------------------

#define MIN_VALID_HEX_STRING_LENGTH     (3)

#define SPACE_CHAR                      ' '
#define NEWLINE_CHAR                    '\n'
#define CARRIAGE_RETURN_CHAR            '\r'

// --------------- Function Prototypes ----------------

#define sprintf sprintf_
int sprintf_(char* buffer, const char* format, ...) ATTRIB_F3CODE;

#define snprintf  snprintf_
#define vsnprintf vsnprintf_
int  snprintf_(char* buffer, size_t count, const char* format, ...) ATTRIB_F3CODE;
int vsnprintf_(char* buffer, size_t count, const char* format, va_list va) ATTRIB_F3CODE;

unsigned int atoi_nano_positive_strict(const char *str, char *was_valid) ATTRIB_F3CODE;
unsigned int atoi_nano_postive(const char* str) ATTRIB_F3CODE;
unsigned int atoi_hex_nano(const char* str) ATTRIB_F3CODE;

signed int chars_prior(const char* str, const char c) ATTRIB_F1CODE;
unsigned int valid_hex_string(const char* str) ATTRIB_F1CODE;

#endif