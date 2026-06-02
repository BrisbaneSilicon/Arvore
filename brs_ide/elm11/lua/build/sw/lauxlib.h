/*
** $Id: lauxlib.h $
** Auxiliary functions for building Lua libraries
** See Copyright Notice in lua.h
*/


#ifndef lauxlib_h
#define lauxlib_h


#include <stddef.h>
#include <stdio.h>

#include "luaconf.h"
#include "lua.h"

#include "ctype.h"


/* global table */
#define LUA_GNAME	"_G"


typedef struct luaL_Buffer luaL_Buffer;


/* extra error code for 'luaL_loadfilex' */
#define LUA_ERRFILE     (LUA_ERRERR+1)


/* key, in the registry, for table of loaded modules */
#define LUA_LOADED_TABLE	"_LOADED"


/* key, in the registry, for table of preloaded loaders */
#define LUA_PRELOAD_TABLE	"_PRELOAD"


typedef struct luaL_Reg {
  const char *name;
  lua_CFunction func;
} luaL_Reg;


#define LUAL_NUMSIZES	(sizeof(lua_Integer)*16 + sizeof(lua_Number))

LUALIB_API void (luaL_checkversion_) (lua_State *L, lua_Number ver, size_t sz) ATTRIB_F1CODE_BUILDSWITCH;
#define luaL_checkversion(L)  \
	  luaL_checkversion_(L, LUA_VERSION_NUM, LUAL_NUMSIZES)

LUALIB_API int (luaL_getmetafield) (lua_State *L, int obj, const char *e) ATTRIB_F1CODE_BUILDSWITCH;
LUALIB_API int (luaL_callmeta) (lua_State *L, int obj, const char *e) ATTRIB_F1CODE_BUILDSWITCH;
LUALIB_API const char *(luaL_tolstring) (lua_State *L, int idx, size_t *len) ATTRIB_F1CODE_BUILDSWITCH;
LUALIB_API int (luaL_argerror) (lua_State *L, int arg, const char *extramsg) ATTRIB_F1CODE_BUILDSWITCH;
LUALIB_API int (luaL_typeerror) (lua_State *L, int arg, const char *tname) ATTRIB_F1CODE_BUILDSWITCH;
LUALIB_API const char *(luaL_checklstring) (lua_State *L, int arg,
                                                          size_t *l) ATTRIB_F1CODE_BUILDSWITCH;
LUALIB_API const char *(luaL_optlstring) (lua_State *L, int arg,
                                          const char *def, size_t *l) ATTRIB_F1CODE_BUILDSWITCH;
LUALIB_API lua_Number (luaL_checknumber) (lua_State *L, int arg) ATTRIB_F1CODE_BUILDSWITCH;
LUALIB_API lua_Number (luaL_optnumber) (lua_State *L, int arg, lua_Number def) ATTRIB_F1CODE_BUILDSWITCH;

LUALIB_API lua_Integer (luaL_checkinteger) (lua_State *L, int arg) ATTRIB_F1CODE_BUILDSWITCH;
LUALIB_API lua_Integer (luaL_optinteger) (lua_State *L, int arg,
                                          lua_Integer def) ATTRIB_F1CODE_BUILDSWITCH;

LUALIB_API void (luaL_checkstack) (lua_State *L, int sz, const char *msg) ATTRIB_F1CODE_BUILDSWITCH;
LUALIB_API void (luaL_checktype) (lua_State *L, int arg, int t) ATTRIB_F1CODE_BUILDSWITCH;
LUALIB_API void (luaL_checkany) (lua_State *L, int arg) ATTRIB_F1CODE_BUILDSWITCH;

LUALIB_API int   (luaL_newmetatable) (lua_State *L, const char *tname) ATTRIB_F1CODE_BUILDSWITCH;
LUALIB_API void  (luaL_setmetatable) (lua_State *L, const char *tname) ATTRIB_F1CODE_BUILDSWITCH;
LUALIB_API void *(luaL_testudata) (lua_State *L, int ud, const char *tname) ATTRIB_F1CODE_BUILDSWITCH;
LUALIB_API void *(luaL_checkudata) (lua_State *L, int ud, const char *tname) ATTRIB_F1CODE_BUILDSWITCH;

LUALIB_API void (luaL_where) (lua_State *L, int lvl) ATTRIB_F1CODE_BUILDSWITCH;
LUALIB_API int (luaL_error) (lua_State *L, const char *fmt, ...) ATTRIB_F1CODE_BUILDSWITCH;
LUALIB_API int (lual_usercancelledprogram_error) (lua_State *L, const char *fmt, ...) ATTRIB_F1CODE_BUILDSWITCH;

LUALIB_API int (luaL_checkoption) (lua_State *L, int arg, const char *def,
                                   const char *const lst[]) ATTRIB_F1CODE_BUILDSWITCH;

LUALIB_API int (luaL_fileresult) (lua_State *L, int stat, const char *fname) ATTRIB_F1CODE_BUILDSWITCH;
LUALIB_API int (luaL_execresult) (lua_State *L, int stat) ATTRIB_F1CODE_BUILDSWITCH;


/* predefined references */
#define LUA_NOREF       (-2)
#define LUA_REFNIL      (-1)

LUALIB_API int (luaL_ref) (lua_State *L, int t) ATTRIB_F1CODE_BUILDSWITCH;
LUALIB_API void (luaL_unref) (lua_State *L, int t, int ref) ATTRIB_F1CODE_BUILDSWITCH;

LUALIB_API int (luaL_loadfilex) (lua_State *L, const char *filename,
                                               const char *mode) ATTRIB_F1CODE_BUILDSWITCH;

#define luaL_loadfile(L,f)	luaL_loadfilex(L,f,NULL)

LUALIB_API int (luaL_loadprogramx) (lua_State *L, const char *progname, uint8_t print_progress) ATTRIB_F1CODE_BUILDSWITCH;

#define luaL_loadprogram(L,p,pp)  luaL_loadprogramx(L,p,pp)

LUALIB_API int (luaL_loadbufferx) (lua_State *L, const char *buff, size_t sz,
                                   const char *name, const char *mode) ATTRIB_F1CODE_BUILDSWITCH;
LUALIB_API int (luaL_loadstring) (lua_State *L, const char *s) ATTRIB_F1CODE_BUILDSWITCH;

LUALIB_API lua_State *(luaL_newstate) (void) ATTRIB_F1CODE_BUILDSWITCH;

LUALIB_API lua_Integer (luaL_len) (lua_State *L, int idx) ATTRIB_F1CODE_BUILDSWITCH;

LUALIB_API void (luaL_addgsub) (luaL_Buffer *b, const char *s,
                                     const char *p, const char *r) ATTRIB_F1CODE_BUILDSWITCH;
LUALIB_API const char *(luaL_gsub) (lua_State *L, const char *s,
                                    const char *p, const char *r) ATTRIB_F1CODE_BUILDSWITCH;

LUALIB_API void (luaL_setfuncs) (lua_State *L, const luaL_Reg *l, int nup) ATTRIB_F1CODE_BUILDSWITCH;
LUALIB_API void (luaL_setfunc) (lua_State *L, const luaL_Reg *l, int nup) ATTRIB_F1CODE_BUILDSWITCH;

LUALIB_API int (luaL_getsubtable) (lua_State *L, int idx, const char *fname) ATTRIB_F1CODE_BUILDSWITCH;

LUALIB_API void (luaL_traceback) (lua_State *L, lua_State *L1,
                                  const char *msg, int level) ATTRIB_F1CODE_BUILDSWITCH;

LUALIB_API void (luaL_dumpallstacklevels) (lua_State *L, lua_State *L1, int level) ATTRIB_F1CODE_BUILDSWITCH;

LUALIB_API void (luaL_requiref) (lua_State *L, const char *modname,
                                 lua_CFunction openf, int glb) ATTRIB_F1CODE_BUILDSWITCH;

/*
** ===============================================================
** some useful macros
** ===============================================================
*/


#define luaL_newlibtable(L,l)	\
  lua_createtable(L, 0, sizeof(l)/sizeof((l)[0]) - 1)

#define luaL_newlib(L,l)  \
  (luaL_checkversion(L), luaL_newlibtable(L,l), luaL_setfuncs(L,l,0))

#define luaL_argcheck(L, cond,arg,extramsg)	\
	((void)(luai_likely(cond) || luaL_argerror(L, (arg), (extramsg))))

#define luaL_argexpected(L,cond,arg,tname)	\
	((void)(luai_likely(cond) || luaL_typeerror(L, (arg), (tname))))

#define luaL_checkstring(L,n)	(luaL_checklstring(L, (n), NULL))
#define luaL_optstring(L,n,d)	(luaL_optlstring(L, (n), (d), NULL))

#define luaL_typename(L,i)	lua_typename(L, lua_type(L,(i)))

#define luaL_dofile(L, fn) \
	(luaL_loadfile(L, fn) || lua_pcall(L, 0, LUA_MULTRET, 0))

#define luaL_dostring(L, s) \
	(luaL_loadstring(L, s) || lua_pcall(L, 0, LUA_MULTRET, 0))

#define luaL_getmetatable(L,n)	(lua_getfield(L, LUA_REGISTRYINDEX, (n)))

#define luaL_opt(L,f,n,d)	(lua_isnoneornil(L,(n)) ? (d) : f(L,(n)))

#define luaL_loadbuffer(L,s,sz,n)	luaL_loadbufferx(L,s,sz,n,NULL)


/*
** Perform arithmetic operations on lua_Integer values with wrap-around
** semantics, as the Lua core does.
*/
#define luaL_intop(op,v1,v2)  \
	((lua_Integer)((lua_Unsigned)(v1) op (lua_Unsigned)(v2)))


/* push the value used to represent failure/error */
#define luaL_pushfail(L)	lua_pushnil(L)


/*
** Internal assertions for in-house debugging
*/
/*#if !defined(lua_assert)

#if defined LUAI_ASSERT
  #include <assert.h>
  #define lua_assert(c)		assert(c)
#else
  #define lua_assert(c)		((void)0)
#endif

#endif*/

/*
** {======================================================
** Generic Buffer manipulation
** =======================================================
*/

struct luaL_Buffer {
  char *b;  /* buffer address */
  size_t size;  /* buffer size */
  size_t n;  /* number of characters in buffer */
  lua_State *L;
  union {
    LUAI_MAXALIGN;  /* ensure maximum alignment for buffer */
    char b[LUAL_BUFFERSIZE];  /* initial buffer */
  } init;
};


#define luaL_bufflen(bf)	((bf)->n)
#define luaL_buffaddr(bf)	((bf)->b)


#define luaL_addchar(B,c) \
  ((void)((B)->n < (B)->size || luaL_prepbuffsize((B), 1)), \
   ((B)->b[(B)->n++] = (c)))

#define luaL_addsize(B,s)	((B)->n += (s))

#define luaL_buffsub(B,s)	((B)->n -= (s))

LUALIB_API void (luaL_buffinit) (lua_State *L, luaL_Buffer *B) ATTRIB_F1CODE_BUILDSWITCH;
LUALIB_API char *(luaL_prepbuffsize) (luaL_Buffer *B, size_t sz) ATTRIB_F1CODE_BUILDSWITCH;
LUALIB_API void (luaL_addlstring) (luaL_Buffer *B, const char *s, size_t l) ATTRIB_F1CODE_BUILDSWITCH;
LUALIB_API void (luaL_addstring) (luaL_Buffer *B, const char *s) ATTRIB_F1CODE_BUILDSWITCH;
LUALIB_API void (luaL_addvalue) (luaL_Buffer *B) ATTRIB_F1CODE_BUILDSWITCH;
LUALIB_API void (luaL_pushresult) (luaL_Buffer *B) ATTRIB_F1CODE_BUILDSWITCH;
LUALIB_API void (luaL_pushresultsize) (luaL_Buffer *B, size_t sz) ATTRIB_F1CODE_BUILDSWITCH;
LUALIB_API char *(luaL_buffinitsize) (lua_State *L, luaL_Buffer *B, size_t sz) ATTRIB_F1CODE_BUILDSWITCH;

#define luaL_prepbuffer(B)	luaL_prepbuffsize(B, LUAL_BUFFERSIZE)

/* }====================================================== */



/*
** {======================================================
** File handles for IO library
** =======================================================
*/

/*
** A file handle is a userdata with metatable 'LUA_FILEHANDLE' and
** initial structure 'luaL_Stream' (it may contain other fields
** after that initial structure).
*/

#define LUA_FILEHANDLE          "FILE*"


typedef struct luaL_Stream {
  FILE *f;  /* stream (NULL for incompletely created streams) */
  lua_CFunction closef;  /* to close stream (NULL for closed streams) */
} luaL_Stream;

/* }====================================================== */

/*
** {==================================================================
** "Abstraction Layer" for basic report of messages and errors
** ===================================================================
*/

/* print a string */
#if !defined(lua_writestring)
#define lua_writestring(s,l)   fwrite((s), sizeof(char), (l), stdout)
#endif

/* print a newline and flush the output */
#if !defined(lua_writeline)
#define lua_writeline()        (lua_writestring(STR_NL_CR, 2), fflush(stdout))
#endif

/* print an error message */
#define lua_writestringerror(s) (uart_write_string(s), uart_write_string(STR_NL_CR))

/* }================================================================== */


/*
** {============================================================
** Compatibility with deprecated conversions
** =============================================================
*/
#if defined(LUA_COMPAT_APIINTCASTS)

#define luaL_checkunsigned(L,a)	((lua_Unsigned)luaL_checkinteger(L,a))
#define luaL_optunsigned(L,a,d)	\
	((lua_Unsigned)luaL_optinteger(L,a,(lua_Integer)(d)))

#define luaL_checkint(L,n)	((int)luaL_checkinteger(L, (n)))
#define luaL_optint(L,n,d)	((int)luaL_optinteger(L, (n), (d)))

#define luaL_checklong(L,n)	((long)luaL_checkinteger(L, (n)))
#define luaL_optlong(L,n,d)	((long)luaL_optinteger(L, (n), (d)))

#endif
/* }============================================================ */


#define DLIB_REBOOT                           "reboot"
#define DLIB_EXIT                             "exit"
#define DLIB_DUMP_STACK                       "dump_stack"
#define DLIB_SET_GPIO                         "set_gpio"
#define DLIB_GET_GPIO                         "get_gpio"
#define DLIB_SET_PWM                          "set_pwm"
#define DLIB_SPI_TX                           "spi_tx"
#define DLIB_SPI_TX_BYTE                      "spi_tx_byte"
#define DLIB_SPI_TX_CHAR                      "spi_tx_char"
#define DLIB_SPI_TX_INT                       "spi_tx_int"
#define DLIB_SPI_RX                           "spi_rx"
#define DLIB_SPI_RX_BYTE                      "spi_rx_byte"
#define DLIB_SPI_RX_BYTE_NONBLOCKING          "spi_rx_byte_nonblocking"
#define DLIB_SPI_RX_CHAR                      "spi_rx_char"
#define DLIB_SPI_RX_CHAR_NONBLOCKING          "spi_rx_char_nonblocking"
#define DLIB_SPI_RX_INT                       "spi_rx_int"
#define DLIB_SPI_RX_INT_NONBLOCKING           "spi_rx_int_nonblocking"
#define DLIB_UART_TX                          "uart_tx"
#define DLIB_UART_TX_CHAR                     "uart_tx_char"
#define DLIB_UART_TX_STRING                   "uart_tx_string"
#define DLIB_UART_TX_BYTE                     "uart_tx_byte"
#define DLIB_UART_TX_INT                      "uart_tx_int"
#define DLIB_UART_RX_BYTE                     "uart_rx_byte"
#define DLIB_UART_RX_BYTE_NONBLOCKING         "uart_rx_byte_nonblocking"
#define DLIB_UART_RX_CHAR                     "uart_rx_char"
#define DLIB_UART_RX_CHAR_NONBLOCKING         "uart_rx_char_nonblocking"
#define DLIB_UART_RX_STRING                   "uart_rx_string"
#define DLIB_LOCK                             "lock"
#define DLIB_LOCK_NONBLOCKING                 "lock_nonblocking"
#define DLIB_UNLOCK                           "unlock"
#define DLIB_UNLOCK_NONBLOCKING               "unlock_nonblocking"
#define DLIB_PIPE_TX_BYTE                     "pipe_tx_byte"
#define DLIB_PIPE_TX_BYTE_NONBLOCKING         "pipe_tx_byte_nonblocking"
#define DLIB_PIPE_RX_BYTE                     "pipe_rx_byte"
#define DLIB_PIPE_RX_BYTE_NONBLOCKING         "pipe_rx_byte_nonblocking"
#define DLIB_GET_ADC                          "get_adc"
#define DLIB_SET_DAC                          "set_dac"
#define DLIB_SLEEP                            "sleep"
#define DLIB_SLEEP_F                          "sleep_f"
#define DLIB_MSLEEP                           "msleep"
#define DLIB_MSLEEP_F                         "msleep_f"
#define DLIB_USLEEP                           "usleep"
#define DLIB_SLEEP_UNINTERRUPTIBLE            "sleep_noint"
#define DLIB_MSLEEP_UNINTERRUPTIBLE           "msleep_noint"
#define DLIB_USLEEP_UNINTERRUPTIBLE           "usleep_noint"
#define DLIB_RESET_HARDWARE_WATCHDOG          "watchdog_reset"
#define DLIB_GET_HARDWARE_WATCHDOG_TIMER_MS   "get_watchdog_timer"
#define DLIB_SET_IO_CONFIG                    "set_io_type_cfg"
#define DLIB_RESET_IO_TYPE                    "reset_io_type_cfg"
#define DLIB_RESET_ALL_IO_TYPES               "reset_all_io_type_cfg"
#define DLIB_SET_INTERRUPT_TYPES_FOR_PIN      "set_interrupt_types_for_pin"
#define DLIB_ENABLE_INTERRUPT_TYPES_FOR_PIN   "enable_interrupt_types_for_pin"
#define DLIB_DISABLE_INTERRUPT_TYPES_FOR_PIN  "disable_interrupt_types_for_pin"
#define DLIB_GET_INTERRUPTS_ON_PIN            "get_interrupts_on_pin"
#define DLIB_ACK_INTERRUPT_TYPES_ON_PIN       "ack_interrupt_types_on_pin"
#define DLIB_ACK_INTERRUPT_TYPES_ON_PINS      "ack_interrupt_types_on_pins"
#define DLIB_GLOBAL_INTERRUPT_ENABLE          "global_interrupt_enable"
#define DLIB_GLOBAL_INTERRUPT_DISABLE         "global_interrupt_disable"
#define DLIB_REPL_INTERRUPT_MODE_ENABLE       "repl_interrupt_mode_enable"
#define DLIB_REPL_INTERRUPT_MODE_DISABLE      "repl_interrupt_mode_disable"
#define DLIB_RUN_PROGRAM                      "run_program"
#define DLIB_FPGA_WRITE                       "fpga_write"
#define DLIB_FPGA_WRITE_NONBLOCKING           "fpga_write_nonblocking"
#define DLIB_FPGA_READ                        "fpga_read"
#define DLIB_FPGA_READ_NONBLOCKING            "fpga_read_nonblocking"

#endif


