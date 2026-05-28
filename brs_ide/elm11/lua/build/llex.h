/*
** $Id: llex.h $
** Lexical Analyzer
** See Copyright Notice in lua.h
*/

#ifndef llex_h
#define llex_h

#include <limits.h>

#include "lobject.h"
#include "lzio.h"


/*
** Single-char tokens (terminal symbols) are represented by their own
** numeric code. Other tokens start at the following value.
*/
#define FIRST_RESERVED	(UCHAR_MAX + 1)


#if !defined(LUA_ENV)
#define LUA_ENV		"_ENV"
#endif


/*
* WARNING: if you change the order of this enumeration,
* grep "ORDER RESERVED"
*/
enum RESERVED {
  /* terminal symbols denoted by reserved words */
  TK_AND = FIRST_RESERVED, TK_BREAK,
  TK_DO, TK_ELSE, TK_ELSEIF, TK_END, TK_FALSE, TK_FOR, TK_FUNCTION,
  TK_GOTO, TK_IF, TK_IN, TK_LOCAL, TK_NIL, TK_NOT, TK_OR, TK_REPEAT,
  TK_RETURN, TK_THEN, TK_TRUE, TK_UNTIL, TK_WHILE,
  /* other terminal symbols */
  TK_IDIV, TK_CONCAT, TK_DOTS, TK_EQ, TK_GE, TK_LE, TK_NE,
  TK_SHL, TK_SHR,
  TK_DBCOLON,
  TK_EOS,
  TK_FLT, TK_INT, TK_NAME, TK_STRING,

  TK_LOW, TK_HIGH, TK_TOGGLE,
  TK_PIN1, TK_PIN2, TK_PIN3, TK_PIN4, TK_PIN5, TK_PIN6, TK_PIN7, TK_PIN8, TK_PIN9,
    TK_PIN10, TK_PIN11, TK_PIN12, TK_PIN13, TK_PIN14, TK_PIN15, TK_PIN16, TK_PIN17, TK_PIN18, TK_PIN19,
      TK_PIN20, TK_PIN21, TK_PIN22, TK_PIN23, TK_PIN24, TK_PIN25, TK_PIN26, TK_PIN27, TK_PIN28, TK_PIN29,
        TK_PIN30, TK_PIN31, TK_PIN32,
  TK_PIN1_BITMASK, TK_PIN2_BITMASK, TK_PIN3_BITMASK, TK_PIN4_BITMASK, TK_PIN5_BITMASK, TK_PIN6_BITMASK, TK_PIN7_BITMASK,
    TK_PIN8_BITMASK, TK_PIN9_BITMASK, TK_PIN10_BITMASK, TK_PIN11_BITMASK, TK_PIN12_BITMASK, TK_PIN13_BITMASK, TK_PIN14_BITMASK,
      TK_PIN15_BITMASK, TK_PIN16_BITMASK, TK_PIN17_BITMASK, TK_PIN18_BITMASK, TK_PIN19_BITMASK, TK_PIN20_BITMASK, TK_PIN21_BITMASK,
        TK_PIN22_BITMASK, TK_PIN23_BITMASK, TK_PIN24_BITMASK, TK_PIN25_BITMASK, TK_PIN26_BITMASK, TK_PIN27_BITMASK, TK_PIN28_BITMASK,
          TK_PIN29_BITMASK, TK_PIN30_BITMASK, TK_PIN31_BITMASK, TK_PIN32_BITMASK,
  TK_NONE, TK_GPIO_OUT, TK_GPIO_IN, TK_PWM, TK_UART_OUT, TK_UART_IN, TK_SPI_OUT, TK_SPI_IN, TK_I2C,
  TK_CORE1, TK_CORE2, TK_CORE3, TK_CORE4, TK_CORE5, TK_CORE6, TK_CORE7, TK_CORE8,
  TK_GPIO_INTRPT_GND, TK_GPIO_INTRPT_VCC, TK_GPIO_INTRPT_RISING_EDGE, TK_GPIO_INTRPT_FALLING_EDGE,
  TK_UART_RX_INTRPT_DATA_AVAILABLE,

  TK_TOTAL_RESERVED
};

//    "and", "break", "do", "else", "elseif",
//    "end", "false", "for", "function", "goto", "if",
//    "in", "local", "nil", "not", "or", "repeat",
//    "return", "then", "true", "until", "while",
//    "//", "..", "...", "==", ">=", "<=", "~=",
//    "<<", ">>", "::", "<eof>",
//    "<number>", "<integer>", "<name>", "<string>"
//    "LOW", "low", "HIGH", "high", "TOGGLE", "toggle"

/* number of reserved words */
#define NUM_RESERVED                          (cast_int(TK_WHILE-FIRST_RESERVED + 1))

#define DTYPE_RSRVD_START_INDEX               (cast_int(TK_LOW-FIRST_RESERVED))
#define DTYPE_RSRVD_END_INDEX                 (cast_int((TK_TOTAL_RESERVED-FIRST_RESERVED) - 1))

#define DTYPE_RSRVD_GPIO_START_INDEX          (cast_int(TK_LOW-FIRST_RESERVED))

#define DTYPE_RSRVD_PIN_START_INDEX           (cast_int(TK_PIN1-FIRST_RESERVED))
#define DTYPE_RSRVD_PIN_END_INDEX             (cast_int(TK_PIN32-FIRST_RESERVED))

#define DTYPE_RSRVD_PIN_BITMASK_START_INDEX   (cast_int(TK_PIN1_BITMASK-FIRST_RESERVED))
#define DTYPE_RSRVD_PIN_BITMASK_END_INDEX     (cast_int(TK_PIN32_BITMASK-FIRST_RESERVED))

#define DTYPE_RSRVD_IO_TYPE_START_INDEX       (cast_int(TK_NONE-FIRST_RESERVED))

#define DTYPE_RSRVD_CORE_TYPE_START_INDEX     (cast_int(TK_CORE1-FIRST_RESERVED))

#define DTYPE_RSRVD_INTRPT_START_INDEX        (cast_int(TK_GPIO_INTRPT_GND-FIRST_RESERVED))


typedef union {
  lua_Number r;
  lua_Integer i;
  TString *ts;
} SemInfo;  /* semantics information */


typedef struct Token {
  int token;
  SemInfo seminfo;
} Token;


/* state of the lexer plus state of the parser when shared by all
   functions */
typedef struct LexState {
  int current;  /* current character (charint) */
  int linenumber;  /* input line counter */
  int lastline;  /* line of last token 'consumed' */
  Token t;  /* current token */
  Token lookahead;  /* look ahead token */
  struct FuncState *fs;  /* current function (parser) */
  struct lua_State *L;
  ZIO *z;  /* input stream */
  Mbuffer *buff;  /* buffer for tokens */
  Table *h;  /* to avoid collection/reuse strings */
  struct Dyndata *dyd;  /* dynamic structures used by the parser */
  TString *source;  /* current source name */
  TString *envn;  /* environment variable name */
} LexState;


LUAI_FUNC void luaX_init (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;
LUAI_FUNC void luaX_setinput (lua_State *L, LexState *ls, ZIO *z,
                              TString *source, int firstchar) ATTRIB_F1CODE_BUILDSWITCH;
LUAI_FUNC TString *luaX_newstring (LexState *ls, const char *str, size_t l) ATTRIB_F1CODE_BUILDSWITCH;
LUAI_FUNC void luaX_next (LexState *ls) ATTRIB_F1CODE_BUILDSWITCH;
LUAI_FUNC int luaX_lookahead (LexState *ls) ATTRIB_F1CODE_BUILDSWITCH;
LUAI_FUNC l_noret luaX_syntaxerror (LexState *ls, const char *s) ATTRIB_F1CODE_BUILDSWITCH;
LUAI_FUNC const char *luaX_token2str (LexState *ls, int token) ATTRIB_F1CODE_BUILDSWITCH;
LUAI_FUNC const char *luaX_tokenstr (int token_index) ATTRIB_F1CODE_BUILDSWITCH;

#endif
