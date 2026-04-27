#ifndef CTYPE_H
#define CTYPE_H

#include <stdio.h>
#include <stdint.h>

#include "config.h"

// --------------- Defines ----------------

#define C_NULL                            (0x00)
#define C_BACKSPACE                       (0x08)
#define C_NEWLINE                         (0x0A)
#define C_CARRIAGE_RETURN                 (0x0D)
#define C_ESCAPE                          (0x1B)
#define C_SPACE                           (0x20)
#define C_ONE                             (0x31)
#define C_TWO                             (0x32)
#define C_THREE                           (0x33)
#define C_UPPERCASE_A                     (0x41)
#define C_UPPERCASE_B                     (0x42)
#define C_UPPERCASE_C                     (0x43)
#define C_UPPERCASE_D                     (0x44)
#define C_SQUARE_BRACKET_OPEN             (0x5B)
#define C_TILDA                           (0x7E)
#define C_DEL                             (0x7F)

#define C_CUSTOM_LEFT_ARROW               (0x11)
#define C_CUSTOM_RIGHT_ARROW              (0x12)
#define C_CUSTOM_UP_ARROW                 (0x13)
#define C_CUSTOM_DOWN_ARROW               (0x14)
#define C_CUSTOM_HOME                     (0x15)
#define C_CUSTOM_END                      (0x16)


// NOTE: EC == Escape Code
#define STR_EC_MOVE_CURSOR_LIMIT          "\033[9999;9999H"
#define STR_EC_QUERY_CURSOR_POSITION      "\033[6n"
#define STR_EC_CLEAR_SCREEN               "\033[2J"
#define STR_EC_CLEAR_SCROLLBACK_BUFFER    "\033[3J"
#define STR_EC_CLEAR_LINE                 "\033[2K"
#define STR_EC_CLEAR_TO_END_OF_LINE       "\033[K"
#define STR_EC_MOVE_TO_0_0                "\033[0;0H"
#define STR_EC_MOVE_UP_ONE_LINE           "\033[1A"
#define STR_EC_MOVE_DOWN_ONE_LINE         "\033[1B"
#define STR_EC_MOVE_FORWARD_ONE_CHAR      "\033[1C"
#define STR_EC_MOVE_BACK_ONE_CHAR         "\033[1D"
#define STR_EC_FONT_BOLD                  "\033[1m"
#define STR_EC_FONT_UNDERLINE             "\033[4m"
#define STR_EC_FONT_INVERT                "\033[7m"
#define STR_EC_FONT_RESET                 "\033[0m"
#define STR_EC_FONT_RST_INTENSITY         "\033[22m"

#define STR_SPACE                         "  "
#define STR_NL                            "\n"
#define STR_CR                            "\r"
#define STR_NL_CR                         "\n\r"
#define STR_PIN                           "PIN"


extern const char *_ctype_;

#if (' ' == 32) && ('!' == 33) && ('"' == 34) && ('#' == 35) \
    && ('%' == 37) && ('&' == 38) && ('\'' == 39) && ('(' == 40) \
    && (')' == 41) && ('*' == 42) && ('+' == 43) && (',' == 44) \
    && ('-' == 45) && ('.' == 46) && ('/' == 47) && ('0' == 48) \
    && ('1' == 49) && ('2' == 50) && ('3' == 51) && ('4' == 52) \
    && ('5' == 53) && ('6' == 54) && ('7' == 55) && ('8' == 56) \
    && ('9' == 57) && (':' == 58) && (';' == 59) && ('<' == 60) \
    && ('=' == 61) && ('>' == 62) && ('?' == 63) && ('A' == 65) \
    && ('B' == 66) && ('C' == 67) && ('D' == 68) && ('E' == 69) \
    && ('F' == 70) && ('G' == 71) && ('H' == 72) && ('I' == 73) \
    && ('J' == 74) && ('K' == 75) && ('L' == 76) && ('M' == 77) \
    && ('N' == 78) && ('O' == 79) && ('P' == 80) && ('Q' == 81) \
    && ('R' == 82) && ('S' == 83) && ('T' == 84) && ('U' == 85) \
    && ('V' == 86) && ('W' == 87) && ('X' == 88) && ('Y' == 89) \
    && ('Z' == 90) && ('[' == 91) && ('\\' == 92) && (']' == 93) \
    && ('^' == 94) && ('_' == 95) && ('a' == 97) && ('b' == 98) \
    && ('c' == 99) && ('d' == 100) && ('e' == 101) && ('f' == 102) \
    && ('g' == 103) && ('h' == 104) && ('i' == 105) && ('j' == 106) \
    && ('k' == 107) && ('l' == 108) && ('m' == 109) && ('n' == 110) \
    && ('o' == 111) && ('p' == 112) && ('q' == 113) && ('r' == 114) \
    && ('s' == 115) && ('t' == 116) && ('u' == 117) && ('v' == 118) \
    && ('w' == 119) && ('x' == 120) && ('y' == 121) && ('z' == 122) \
    && ('{' == 123) && ('|' == 124) && ('}' == 125) && ('~' == 126)
/* The character set is ASCII or one of its variants or extensions, not EBCDIC.
   Testing the value of '\n' and '\r' is not relevant.  */
# define C_CTYPE_ASCII 1
#elif ! (' ' == '\x40' && '0' == '\xf0'                     \
         && 'A' == '\xc1' && 'J' == '\xd1' && 'S' == '\xe2' \
         && 'a' == '\x81' && 'j' == '\x91' && 's' == '\xa2')
# error "Only ASCII and EBCDIC are supported"
#endif

#if 'A' < 0
# error "EBCDIC and char is signed -- not supported"
#endif

/* Cases for control characters.  */

#define _C_CTYPE_CNTRL \
   case '\a': case '\b': case '\f': case '\n': \
   case '\r': case '\t': case '\v': \
   _C_CTYPE_OTHER_CNTRL

/* ASCII control characters other than those with \-letter escapes.  */

#if C_CTYPE_ASCII
# define _C_CTYPE_OTHER_CNTRL \
    case '\x00': case '\x01': case '\x02': case '\x03': \
    case '\x04': case '\x05': case '\x06': case '\x0e': \
    case '\x0f': case '\x10': case '\x11': case '\x12': \
    case '\x13': case '\x14': case '\x15': case '\x16': \
    case '\x17': case '\x18': case '\x19': case '\x1a': \
    case '\x1b': case '\x1c': case '\x1d': case '\x1e': \
    case '\x1f': case '\x7f'
#else
   /* Use EBCDIC code page 1047's assignments for ASCII control chars;
      assume all EBCDIC code pages agree about these assignments.  */
# define _C_CTYPE_OTHER_CNTRL \
    case '\x00': case '\x01': case '\x02': case '\x03': \
    case '\x07': case '\x0e': case '\x0f': case '\x10': \
    case '\x11': case '\x12': case '\x13': case '\x18': \
    case '\x19': case '\x1c': case '\x1d': case '\x1e': \
    case '\x1f': case '\x26': case '\x27': case '\x2d': \
    case '\x2e': case '\x32': case '\x37': case '\x3c': \
    case '\x3d': case '\x3f'
#endif

/* Cases for lowercase hex letters, and lowercase letters, all offset by N.  */

#define _C_CTYPE_LOWER_A_THRU_F_N(n) \
   case 'a' + (n): case 'b' + (n): case 'c' + (n): case 'd' + (n): \
   case 'e' + (n): case 'f' + (n)
#define _C_CTYPE_LOWER_N(n) \
   _C_CTYPE_LOWER_A_THRU_F_N(n): \
   case 'g' + (n): case 'h' + (n): case 'i' + (n): case 'j' + (n): \
   case 'k' + (n): case 'l' + (n): case 'm' + (n): case 'n' + (n): \
   case 'o' + (n): case 'p' + (n): case 'q' + (n): case 'r' + (n): \
   case 's' + (n): case 't' + (n): case 'u' + (n): case 'v' + (n): \
   case 'w' + (n): case 'x' + (n): case 'y' + (n): case 'z' + (n)

/* Cases for hex letters, digits, lower, punct, and upper.  */

#define _C_CTYPE_A_THRU_F \
   _C_CTYPE_LOWER_A_THRU_F_N (0): \
   _C_CTYPE_LOWER_A_THRU_F_N ('A' - 'a')
#define _C_CTYPE_DIGIT                     \
   case '0': case '1': case '2': case '3': \
   case '4': case '5': case '6': case '7': \
   case '8': case '9'
#define _C_CTYPE_LOWER _C_CTYPE_LOWER_N (0)
#define _C_CTYPE_PUNCT \
   case '!': case '"': case '#': case '$':  \
   case '%': case '&': case '\'': case '(': \
   case ')': case '*': case '+': case ',':  \
   case '-': case '.': case '/': case ':':  \
   case ';': case '<': case '=': case '>':  \
   case '?': case '@': case '[': case '\\': \
   case ']': case '^': case '_': case '`':  \
   case '{': case '|': case '}': case '~'
#define _C_CTYPE_UPPER _C_CTYPE_LOWER_N ('A' - 'a')


// --------------- Function Prototypes ----------------

int isalnum (int c) ATTRIB_F3CODE;
int isalpha (int c) ATTRIB_F3CODE;
int isascii (int c) ATTRIB_F3CODE;
int isblank (int c) ATTRIB_F3CODE;
int iscntrl (int c) ATTRIB_F3CODE;
int isdigit (int c) ATTRIB_F3CODE;
int isgraph (int c) ATTRIB_F3CODE;
int islower (int c) ATTRIB_F3CODE;
int isprint (int c) ATTRIB_F3CODE;
int ispunct (int c) ATTRIB_F3CODE;
int isspace (int c) ATTRIB_F3CODE;
int isupper (int c) ATTRIB_F3CODE;
int isxdigit (int c) ATTRIB_F3CODE;
int tolower (int c) ATTRIB_F3CODE;
int toupper (int c) ATTRIB_F3CODE;

#endif