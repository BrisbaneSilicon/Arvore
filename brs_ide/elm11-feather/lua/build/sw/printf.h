#ifndef PRINTF_H
#define PRINTF_H

#include <stdarg.h>
#include <stddef.h>

#include "config.h"

#define MIN_VALID_HEX_STRING_LENGTH     (3)

#define SPACE_CHAR                      ' '
#define NEWLINE_CHAR                    '\n'
#define CARRIAGE_RETURN_CHAR            '\r'

/**
 * Tiny sprintf implementation
 * Due to security reasons (buffer overflow) YOU SHOULD CONSIDER USING (V)SNPRINTF INSTEAD!
 * \param buffer A pointer to the buffer where to store the formatted string. MUST be big enough to store the output!
 * \param format A string that specifies the format of the output
 * \return The number of characters that are WRITTEN into the buffer, not counting the terminating null character
 */
#define sprintf sprintf_
int sprintf_(char* buffer, const char* format, ...) ATTRIB_F3CODE;


/**
 * Tiny snprintf/vsnprintf implementation
 * \param buffer A pointer to the buffer where to store the formatted string
 * \param count The maximum number of characters to store in the buffer, including a terminating null character
 * \param format A string that specifies the format of the output
 * \param va A value identifying a variable arguments list
 * \return The number of characters that COULD have been written into the buffer, not counting the terminating
 *         null character. A value equal or larger than count indicates truncation. Only when the returned value
 *         is non-negative and less than count, the string has been completely written.
 */
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