/*
** $Id: lua.h $
** Lua - A Scripting Language
** Lua.org, PUC-Rio, Brazil (http://www.lua.org)
** See Copyright Notice at the end of this file
*/


#ifndef lua_h
#define lua_h

#include <stdarg.h>
#include <stddef.h>

#include "luaconf.h"

#include "io.h"

#define LUA_VERSION_MAJOR	"5"
#define LUA_VERSION_MINOR	"4"
#define LUA_VERSION_RELEASE	"6"

#define LUA_VERSION_NUM			504
#define LUA_VERSION_RELEASE_NUM		(LUA_VERSION_NUM * 100 + 6)

#define LUA_VERSION	"Lua " LUA_VERSION_MAJOR "." LUA_VERSION_MINOR
#define LUA_RELEASE	LUA_VERSION "." LUA_VERSION_RELEASE
#define LUA_COPYRIGHT	LUA_RELEASE "  Copyright (C) 1994-2023 Lua.org, PUC-Rio"
#define LUA_AUTHORS	"R. Ierusalimschy, L. H. de Figueiredo, W. Celes"


/* mark for precompiled code ('<esc>Lua') */
#define LUA_SIGNATURE	"\x1bLua"

/* option for multiple returns in 'lua_pcall' and 'lua_call' */
#define LUA_MULTRET	(-1)

#ifdef TD_GW1NR_9_C7I6_B
    #define MAX_HISTORY_LINES                       (4)
    #define MAX_HISTORY_SINGLE_ENTRY_LINE_CHARS     (64)
#else
    #define MAX_HISTORY_LINES                       (10)
    #define MAX_HISTORY_SINGLE_ENTRY_LINE_CHARS     (128)
#endif

/*
** Pseudo-indices
** (-LUAI_MAXSTACK is the minimum valid index; we keep some free empty
** space after that to help overflow detection)
*/
#define LUA_REGISTRYINDEX	(-LUAI_MAXSTACK - 1000)
#define lua_upvalueindex(i)	(LUA_REGISTRYINDEX - (i))


/* thread status */
#define LUA_OK          (0)
#define LUA_YIELD       (1)
#define LUA_ERRRUN      (2)
#define LUA_ERRSYNTAX   (3)
#define LUA_ERRMEM      (4)
#define LUA_ERRERR      (5)
#define LUA_NO_INPUT    (6)
#define LUA_EOF         (7)
#define LUA_EXIT        (8)


typedef struct lua_State lua_State;
typedef struct lvm_State lvm_State;


/*
** basic types
*/
#define LUA_TNONE                           (-1)

#define LUA_TNIL                            (0)
#define LUA_TBOOLEAN                        (1)
#define LUA_TLIGHTUSERDATA                  (2)
#define LUA_TNUMBER                         (3)
#define LUA_TSTRING                         (4)
#define LUA_TTABLE                          (5)
#define LUA_TFUNCTION                       (6)
#define LUA_TUSERDATA                       (7)
#define LUA_TTHREAD                         (8)
#define LUA_TDWEEZLE_GPIO                   (9)
#define LUA_TDWEEZLE_DIGITAL_PIN            (10)
#define LUA_TDWEEZLE_DIGITAL_PIN_BITMASK    (11)
#define LUA_TDWEEZLE_DIGITAL_PIN_TYPE       (12)
#define LUA_TDWEEZLE_CORE_TYPE              (13)
#define LUA_TDWEEZLE_DIGITAL_INTERRUPT      (14)

#define LUA_NUMTYPES                        (15)
    // WARNING!! The value can't go beyond 6 bits
    // as it will interfere with 'BIT_ISCOLLECTABLE'.. ?


/* minimum Lua stack available to a C function */
#define LUA_MINSTACK	20


/* predefined values in the registry */
#define LUA_RIDX_MAINTHREAD	1
#define LUA_RIDX_GLOBALS	2
#define LUA_RIDX_LAST		LUA_RIDX_GLOBALS


/* type of numbers in Lua */
typedef LUA_NUMBER lua_Number;


/* type for integer functions */
typedef LUA_INTEGER lua_Integer;

/* unsigned integer type */
typedef LUA_UNSIGNED lua_Unsigned;

/* type for continuation-function contexts */
typedef LUA_KCONTEXT lua_KContext;


/*
** Type for C functions registered with Lua
*/
typedef int (*lua_CFunction) (lua_State *L);

/*
** Type for continuation functions
*/
typedef int (*lua_KFunction) (lua_State *L, int status, lua_KContext ctx);


/*
** Type for functions that read/write blocks when loading/dumping Lua chunks
*/
typedef const char * (*lua_Reader) (lua_State *L, void *ud, size_t *sz);

typedef int (*lua_Writer) (lua_State *L, const void *p, size_t sz, void *ud);


/*
** Type for memory-allocation functions
*/
typedef void * (*lua_Alloc) (void *ud, void *ptr, size_t osize, size_t nsize);


/*
** Type for warning functions
*/
typedef void (*lua_WarnFunction) (void *ud, const char *msg, int tocont);


/*
** Type used by the debug API to collect debug information
*/
typedef struct lua_Debug lua_Debug;


/*
** Functions to be called by the debugger in specific events
*/
typedef void (*lua_Hook) (lua_State *L, lua_Debug *ar);

/*
** generic extra include file
*/
#if defined(LUA_USER_H)
#include LUA_USER_H
#endif


/*
** RCS ident string
*/
extern const char lua_ident[];


void l_lineactions (void) ATTRIB_RUNTIMECODE;
void l_checkandhandleswinterrupt (lua_State *L) ATTRIB_RUNTIMECODE;


void l_prelvmactions (void) ATTRIB_F1CODE_BUILDSWITCH;
void l_postlvmactions (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;

void l_usercancelledprogram (void) ATTRIB_F1CODE_BUILDSWITCH;

/*
** state manipulation
*/
LUA_API lua_State *(lua_newstate) (lua_Alloc f, void *ud) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API void       (lua_close) (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API lua_State *(lua_newthread) (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API int        (lua_closethread) (lua_State *L, lua_State *from) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API int        (lua_resetthread) (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;  /* Deprecated! */

LUA_API lua_CFunction (lua_atpanic) (lua_State *L, lua_CFunction panicf) ATTRIB_F1CODE_BUILDSWITCH;


LUA_API lua_Number (lua_version) (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;


/*
** basic stack manipulation
*/
LUA_API int   (lua_absindex) (lua_State *L, int idx) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API int   (lua_gettop) (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API void  (lua_settop) (lua_State *L, int idx) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API void  (lua_pushvalue) (lua_State *L, int idx) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API void  (lua_rotate) (lua_State *L, int idx, int n) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API void  (lua_copy) (lua_State *L, int fromidx, int toidx) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API int   (lua_checkstack) (lua_State *L, int n) ATTRIB_F1CODE_BUILDSWITCH;

LUA_API void  (lua_xmove) (lua_State *from, lua_State *to, int n) ATTRIB_F1CODE_BUILDSWITCH;


/*
** access functions (stack -> C)
*/

LUA_API int             (lua_isnumber) (lua_State *L, int idx) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API int             (lua_isstring) (lua_State *L, int idx) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API int             (lua_iscfunction) (lua_State *L, int idx) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API int             (lua_isinteger) (lua_State *L, int idx) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API int             (lua_isuserdata) (lua_State *L, int idx) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API int             (lua_type) (lua_State *L, int idx) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API const char     *(lua_typename) (lua_State *L, int tp) ATTRIB_F1CODE_BUILDSWITCH;

LUA_API lua_Number      (lua_tonumberx) (lua_State *L, int idx, int *isnum) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API lua_Integer     (lua_tointegerx) (lua_State *L, int idx, int *isnum) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API int             (lua_toboolean) (lua_State *L, int idx) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API const char     *(lua_tolstring) (lua_State *L, int idx, size_t *len) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API lua_Unsigned    (lua_rawlen) (lua_State *L, int idx) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API lua_CFunction   (lua_tocfunction) (lua_State *L, int idx) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API void	       *(lua_touserdata) (lua_State *L, int idx) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API lua_State      *(lua_tothread) (lua_State *L, int idx) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API const void     *(lua_topointer) (lua_State *L, int idx) ATTRIB_F1CODE_BUILDSWITCH;


/*
** Comparison and arithmetic functions
*/

#define LUA_OPADD	0	/* ORDER TM, ORDER OP */
#define LUA_OPSUB	1
#define LUA_OPMUL	2
#define LUA_OPMOD	3
#define LUA_OPPOW	4
#define LUA_OPDIV	5
#define LUA_OPIDIV	6
#define LUA_OPBAND	7
#define LUA_OPBOR	8
#define LUA_OPBXOR	9
#define LUA_OPSHL	10
#define LUA_OPSHR	11
#define LUA_OPUNM	12
#define LUA_OPBNOT	13

LUA_API void  (lua_arith) (lua_State *L, int op) ATTRIB_F1CODE_BUILDSWITCH;

#define LUA_OPEQ	0
#define LUA_OPLT	1
#define LUA_OPLE	2

LUA_API int   (lua_rawequal) (lua_State *L, int idx1, int idx2) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API int   (lua_compare) (lua_State *L, int idx1, int idx2, int op) ATTRIB_F1CODE_BUILDSWITCH;


/*
** push functions (C -> stack)
*/
LUA_API void        (lua_pushnil) (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API void        (lua_pushnumber) (lua_State *L, lua_Number n) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API void        (lua_pushinteger) (lua_State *L, lua_Integer n) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API const char *(lua_pushlstring) (lua_State *L, const char *s, size_t len) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API const char *(lua_pushstring) (lua_State *L, const char *s) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API const char *(lua_pushvfstring) (lua_State *L, const char *fmt,
                                                      va_list argp) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API const char *(lua_pushfstring) (lua_State *L, const char *fmt, ...) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API void  (lua_pushcclosure) (lua_State *L, lua_CFunction fn, int n) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API void  (lua_pushboolean) (lua_State *L, int b) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API void  (lua_pushlightuserdata) (lua_State *L, void *p) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API int   (lua_pushthread) (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;


/*
** get functions (Lua -> stack)
*/
LUA_API int (lua_getglobal) (lua_State *L, const char *name) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API int (lua_gettable) (lua_State *L, int idx) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API int (lua_getfield) (lua_State *L, int idx, const char *k) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API int (lua_geti) (lua_State *L, int idx, lua_Integer n) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API int (lua_rawget) (lua_State *L, int idx) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API int (lua_rawgeti) (lua_State *L, int idx, lua_Integer n) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API int (lua_rawgetp) (lua_State *L, int idx, const void *p) ATTRIB_F1CODE_BUILDSWITCH;

LUA_API void  (lua_createtable) (lua_State *L, int narr, int nrec) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API void *(lua_newuserdatauv) (lua_State *L, size_t sz, int nuvalue) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API int   (lua_getmetatable) (lua_State *L, int objindex) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API int  (lua_getiuservalue) (lua_State *L, int idx, int n) ATTRIB_F1CODE_BUILDSWITCH;


/*
** set functions (stack -> Lua)
*/
LUA_API void  (lua_setglobal) (lua_State *L, const char *name) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API void  (lua_settable) (lua_State *L, int idx) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API void  (lua_setfield) (lua_State *L, int idx, const char *k) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API void  (lua_seti) (lua_State *L, int idx, lua_Integer n) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API void  (lua_rawset) (lua_State *L, int idx) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API void  (lua_rawseti) (lua_State *L, int idx, lua_Integer n) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API void  (lua_rawsetp) (lua_State *L, int idx, const void *p) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API int   (lua_setmetatable) (lua_State *L, int objindex) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API int   (lua_setiuservalue) (lua_State *L, int idx, int n) ATTRIB_F1CODE_BUILDSWITCH;


/*
** 'load' and 'call' functions (load and run Lua code)
*/
LUA_API void  (lua_callk) (lua_State *L, int nargs, int nresults,
                           lua_KContext ctx, lua_KFunction k) ATTRIB_F1CODE_BUILDSWITCH;
#define lua_call(L,n,r)		lua_callk(L, (n), (r), 0, NULL)

LUA_API int   (lua_pcallk) (lua_State *L, int nargs, int nresults, int errfunc,
                            lua_KContext ctx, lua_KFunction k) ATTRIB_F1CODE_BUILDSWITCH;
#define lua_pcall(L,n,r,f)	lua_pcallk(L, (n), (r), (f), 0, NULL)

LUA_API int   (lua_load) (lua_State *L, lua_Reader reader, void *dt,
                          const char *chunkname, const char *mode) ATTRIB_F1CODE_BUILDSWITCH;

LUA_API int (lua_dump) (lua_State *L, lua_Writer writer, void *data, int strip) ATTRIB_F1CODE_BUILDSWITCH;


/*
** coroutine functions
*/
LUA_API int  (lua_yieldk)     (lua_State *L, int nresults, lua_KContext ctx,
                               lua_KFunction k) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API int  (lua_resume)     (lua_State *L, lua_State *from, int narg,
                               int *nres) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API int  (lua_status)     (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API int (lua_isyieldable) (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;

#define lua_yield(L,n)		lua_yieldk(L, (n), 0, NULL)


/*
** Warning-related functions
*/
LUA_API void (lua_setwarnf) (lua_State *L, lua_WarnFunction f, void *ud) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API void (lua_warning)  (lua_State *L, const char *msg, int tocont) ATTRIB_F1CODE_BUILDSWITCH;


/*
** garbage-collection function and options
*/

#define LUA_GCSTOP		0
#define LUA_GCRESTART		1
#define LUA_GCCOLLECT		2
#define LUA_GCCOUNT		3
#define LUA_GCCOUNTB		4
#define LUA_GCSTEP		5
#define LUA_GCSETPAUSE		6
#define LUA_GCSETSTEPMUL	7
#define LUA_GCISRUNNING		9
#define LUA_GCGEN		10
#define LUA_GCINC		11

LUA_API int (lua_gc) (lua_State *L, int what, ...) ATTRIB_F1CODE_BUILDSWITCH;


/*
** miscellaneous functions
*/

LUA_API int   (lua_error) (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;

LUA_API int   (lua_next) (lua_State *L, int idx) ATTRIB_F1CODE_BUILDSWITCH;

LUA_API void  (lua_concat) (lua_State *L, int n) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API void  (lua_len)    (lua_State *L, int idx) ATTRIB_F1CODE_BUILDSWITCH;

LUA_API size_t   (lua_stringtonumber) (lua_State *L, const char *s) ATTRIB_F1CODE_BUILDSWITCH;

LUA_API lua_Alloc (lua_getallocf) (lua_State *L, void **ud) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API void      (lua_setallocf) (lua_State *L, lua_Alloc f, void *ud) ATTRIB_F1CODE_BUILDSWITCH;

LUA_API void (lua_toclose) (lua_State *L, int idx) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API void (lua_closeslot) (lua_State *L, int idx) ATTRIB_F1CODE_BUILDSWITCH;


/*
** {==============================================================
** some useful macros
** ===============================================================
*/

#define lua_getextraspace(L)	((void *)((char *)(L) - LUA_EXTRASPACE))

#define lua_tonumber(L,i)	lua_tonumberx(L,(i),NULL)
#define lua_tointeger(L,i)	lua_tointegerx(L,(i),NULL)

#define lua_pop(L,n)		lua_settop(L, -(n)-1)

#define lua_newtable(L)		lua_createtable(L, 0, 0)

#define lua_register(L,n,f) (lua_pushcfunction(L, (f)), lua_setglobal(L, (n)))

#define lua_pushcfunction(L,f)	lua_pushcclosure(L, (f), 0)

#define lua_isfunction(L,n)	(lua_type(L, (n)) == LUA_TFUNCTION)
#define lua_istable(L,n)	(lua_type(L, (n)) == LUA_TTABLE)
#define lua_islightuserdata(L,n)	(lua_type(L, (n)) == LUA_TLIGHTUSERDATA)
#define lua_isnil(L,n)		(lua_type(L, (n)) == LUA_TNIL)
#define lua_isboolean(L,n)	(lua_type(L, (n)) == LUA_TBOOLEAN)
#define lua_isthread(L,n)	(lua_type(L, (n)) == LUA_TTHREAD)
#define lua_isnone(L,n)		(lua_type(L, (n)) == LUA_TNONE)
#define lua_isnoneornil(L, n)	(lua_type(L, (n)) <= 0)
#define lua_isdweezle(L, n) (lua_type(L, (n)) == LUA_TDWEEZLE)

#define lua_pushliteral(L, s)	lua_pushstring(L, "" s)

#define lua_pushglobaltable(L)  \
	((void)lua_rawgeti(L, LUA_REGISTRYINDEX, LUA_RIDX_GLOBALS))

#define lua_tostring(L,i)	lua_tolstring(L, (i), NULL)


#define lua_insert(L,idx)	lua_rotate(L, (idx), 1)

#define lua_remove(L,idx)	(lua_rotate(L, (idx), -1), lua_pop(L, 1))

#define lua_replace(L,idx)	(lua_copy(L, -1, (idx)), lua_pop(L, 1))

/* }============================================================== */


/*
** {==============================================================
** compatibility macros
** ===============================================================
*/
#if defined(LUA_COMPAT_APIINTCASTS)

#define lua_pushunsigned(L,n)	lua_pushinteger(L, (lua_Integer)(n))
#define lua_tounsignedx(L,i,is)	((lua_Unsigned)lua_tointegerx(L,i,is))
#define lua_tounsigned(L,i)	lua_tounsignedx(L,(i),NULL)

#endif

#define lua_newuserdata(L,s)	lua_newuserdatauv(L,s,1)
#define lua_getuservalue(L,idx)	lua_getiuservalue(L,idx,1)
#define lua_setuservalue(L,idx)	lua_setiuservalue(L,idx,1)

#define LUA_NUMTAGS		LUA_NUMTYPES

/*
** {======================================================================
** Commands !
** =======================================================================
*/

// NOTE: if more commands are added, ensure that the 'help' man page
// is updated with the info !

#define STR_HELP                                        "help"

#define COMMAND_MODE_ENABLE                             "command"
#define COMMAND_MODE_ENABLE_SHORTFORM                   "cmd"
#define COMMAND_MODE_DISABLE                            "exit"


// NOTE: memory category
#define CMD_MEMORY_CATEGORY                             "memory"

#define CMD_MEMORY_FREE                                 "free"
#define CMD_MEMORY_TOTAL                                "total"
#define CMD_MEMORY_FREE_MIN_OBSERVED                    "low_water_mark"
#define CMD_RESET_MEMORY_FREE_MIN_OBSERVED              "reset_low_water_mark"

#define CMD_PRINT_FHEAP_MEM_STATE                       "list_fast_heap_state"
#define CMD_PRINT_FHEAP_MEM_ALLOC_OCCRNS                "list_fast_heap_allocs"
#define CMD_RESET_FHEAP_MEM_ALLOC_OCCRNS                "reset_fast_heap_allocs"
#define CMD_PRINT_HEAP_MEM_ALLOC_OCCRNS                 "list_heap_allocs"
#define CMD_RESET_HEAP_MEM_ALLOC_OCCRNS                 "reset_heap_allocs"
#define CMD_SET_MEMORY_ALLOC_OCCRNS_TRACK_ACCUM         "trace_allocs_cumulative"
#define CMD_SET_MEMORY_ALLOC_OCCRNS_TRACK_NONACCUM      "trace_allocs_non_cumulative"


// NOTE: stack category
#define CMD_STACK_CATEGORY                              "stack"

#define CMD_STACK_TOTAL                                 "total"
#define CMD_STACK_LOW_WATER_MARK                        "low_water_mark"
#define CMD_RESET_STACK_LOW_WATER_MARK                  "reset_low_water_mark"

// NOTE: list category
#define CMD_LIST_CATEGORY                               "list"

#define CMD_HELP                                        "help"
#define CMD_LIST_COMMANDS                               "commands"
#define CMD_REPL_HISTORY                                "repl_history"
#define CMD_CMD_HISTORY                                 "cmd_history"
#define CMD_LIST_PIN_CAPABILITIES                       "io_capabilities"
#define CMD_LIST_PIN_CAPS                               "io_caps"
#define CMD_LIST_PIN_TYPE_CONFIG                        "io_type_cfg"
#define CMD_LIST_PIN_BAUD_CONFIG                        "io_baud_cfg"
#define CMD_LIST_PIN_PWM_CONFIG                         "io_pwm_cfg"
#define CMD_LIST_PIN_SPI_CONFIG                         "io_spi_cfg"
#define CMD_LIST_BUS_CONFIG                             "bus_cfg"
#define CMD_LIST_WATCHDOG_CONFIG                        "watchdog_cfg"
#define CMD_LIST_XBAR_CONFIG                            "xbar_cfg"
#define CMD_LIST_TIMER_CONFIG                           "timer_cfg"
#define CMD_LIST_USER_COMMS_CONFIG                      "user_comms_cfg"
#define CMD_NUM_PROGRAMS                                "program_count"
#define CMD_LIST_PROGRAMS                               "programs"
#define CMD_LIST_PROGRAMS_ADDRS_LOCS                    "program_addresses"
#define CMD_LIST_PROGRAM_DATA_SLOTS                     "program_data_slots"
#define CMD_LIST_START_ON_BOOT_PROMPT_FORMAT            "start_on_boot_prompt_format"
#define CMD_LIST_START_ON_BOOT_PROGRAM                  "start_on_boot_program"
#define CMD_PRINT_PROGRAM                               "program_code"
#define CMD_PRINT_PROGRAM_WITH_OPEN_BRACKET             CMD_PRINT_PROGRAM"(\""
#define CMD_PRINT_PROGRAM_BYTECODE                      "program_bytecode"
#define CMD_PRINT_PROGRAM_BYTECODE_WITH_OPEN_BRACKET    CMD_PRINT_PROGRAM_BYTECODE"(\""
#define CMD_LIST_MEMORY_LAYOUT                          "memory_layout"
#define CMD_LIST_CPU_CLK_FREQUENCY                      "clk_freq"
#define CMD_LIST_GENERIC_DEBUG                          "generic_debug"
#define CMD_LIST_SPI_XIP_DEBUG                          "spi_xip_debug"
#define CMD_LIST_MBUS_DEBUG                             "mbus_debug"
    // NOTE: anything with a 'DEBUG' suffix will
    // only be present if enabled by the FPGA
    // build... otherwise will lock things up!


// NOTE: run category

#define CMD_RUN_CATEGORY                                "run"

#define CMD_RUN_REBOOT                                  "reboot"
#define CMD_RUN_PROGRAM                                 "program"
#define CMD_RUN_PROGRAM_WITH_OPEN_BRACKET               CMD_RUN_PROGRAM"(\""


// NOTE: cycle category

#define CMD_CYCLE_CATEGORY                              "cycle"

#define CMD_CYCLE_CPU_PROMPT_PREFIX_TOGGLE              "cpuprompt"
#define CMD_CYCLE_TIME_PROMPT_PREFIX_TOGGLE             "timeprompt"


// NOTE: set category

#define CMD_SET_CATEGORY                                "set"

#define CMD_SET_IO_TYPE                                 "io_type_cfg"
#define CMD_SET_IO_TYPE_WITH_OPEN_BRACKET               CMD_SET_IO_TYPE"("
#define CMD_SET_IO_BAUD                                 "io_baud_cfg"
#define CMD_SET_IO_BAUD_WITH_OPEN_BRACKET               CMD_SET_IO_BAUD"("
#define CMD_SET_IO_PWM_FREQ                             "io_pwm_cfg"
#define CMD_SET_IO_PWM_FREQ_WITH_OPEN_BRACKET           CMD_SET_IO_PWM_FREQ"("
#define CMD_SET_IO_SPI_FREQ                             "io_spi_cfg"
#define CMD_SET_IO_SPI_FREQ_WITH_OPEN_BRACKET           CMD_SET_IO_SPI_FREQ"("
#define CMD_SET_START_ON_BOOT_PROMPT_FORMAT             "start_on_boot_prompt_format"
#define CMD_SET_START_ON_BOOT_PIN_CONFIG                "start_on_boot_io_type_cfg"
#define CMD_SET_START_ON_BOOT_PROGRAM                   "start_on_boot_program"
#define CMD_SET_START_ON_BOOT_PROGRAM_WITH_OPEN_BRACKET CMD_SET_START_ON_BOOT_PROGRAM"(\""


// NOTE: reset category

#define CMD_RESET_CATEGORY                              "reset"

#define CMD_RESET_START_ON_BOOT_PROMPT_FORMAT           "start_on_boot_prompt_format"
#define CMD_RESET_START_ON_BOOT_IO_CONFIG               "start_on_boot_io_type_cfg"
#define CMD_RESET_START_ON_BOOT_PROGRAM                 "start_on_boot_program"
#define CMD_RESET_ALL_IO_TYPE_CONFIG                    "all_io_type_cfg"
#define CMD_RESET_IO_TYPE_CONFIG                        "io_type_cfg"
#define CMD_RESET_IO_TYPE_CONFIG_WITH_OPEN_BRACKET      CMD_RESET_IO_TYPE_CONFIG"("


// NOTE: load category

#define CMD_LOAD_CATEGORY                               "load"

#define CMD_LOAD_START_ON_BOOT_PIN_CONFIG               "start_on_boot_io_type_cfg"


// NOTE: upload category

#define CMD_UPLOAD_CATEGORY                             "upload"

#define CMD_UPLOAD_PROGRAM                              "program"
#define CMD_UPLOAD_PROGRAM_WITH_OPEN_BRACKET            CMD_UPLOAD_PROGRAM"(\""


// NOTE: delete category

#define CMD_DELETE_CATEGORY                             "delete"

#define CMD_DELETE_ALL_PROGRAMS                         "all_programs"
#define CMD_DELETE_PROGRAM                              "program"
#define CMD_DELETE_PROGRAM_WITH_OPEN_BRACKET            CMD_DELETE_PROGRAM"(\""

// NOTE: don't care about consistent formatting for these,
// as the end user shouldn't be using them...
#define CMD_WRITE_FPGA_REGISTER                         "write_fpga_reg"STR_SPACE
#define CMD_READ_FPGA_REGISTER                          "read_fpga_reg"STR_SPACE

#define STR_COMMAND_MODE_BANNER                         "COMMAND MODE | Type 'exit' to return to REPL | Type 'list|commands' to print a \
short-list of commands | Type 'list|help' to print a detailed list of commands"

/*
** {======================================================================
** Debug API
** =======================================================================
*/


/*
** Event codes
*/
#define LUA_HOOKCALL        0
#define LUA_HOOKRET         1
#define LUA_HOOKLINE1       2
#define LUA_HOOKLINE2       3
#define LUA_HOOKCOUNT       4
#define LUA_HOOKTAILCALL    5


/*
** Event masks
*/
#define LUA_MASKCALL    (0 << LUA_HOOKCALL)
#define LUA_MASKRET	    (0 << LUA_HOOKRET)
#define LUA_MASKLINE1   (1 << LUA_HOOKLINE1)
#define LUA_MASKLINE2   (1 << LUA_HOOKLINE2)
#define LUA_MASKCOUNT   (0 << LUA_HOOKCOUNT)
    // NOTE: unused are disabled...

LUA_API int (lua_getstack) (lua_State *L, int level, lua_Debug *ar) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API int (lua_getinfo) (lua_State *L, const char *what, lua_Debug *ar) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API const char *(lua_getlocal) (lua_State *L, const lua_Debug *ar, int n) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API const char *(lua_setlocal) (lua_State *L, const lua_Debug *ar, int n) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API const char *(lua_getupvalue) (lua_State *L, int funcindex, int n) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API const char *(lua_setupvalue) (lua_State *L, int funcindex, int n) ATTRIB_F1CODE_BUILDSWITCH;

LUA_API void *(lua_upvalueid) (lua_State *L, int fidx, int n) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API void  (lua_upvaluejoin) (lua_State *L, int fidx1, int n1,
                                               int fidx2, int n2) ATTRIB_F1CODE_BUILDSWITCH;

LUA_API void (lua_sethook) (lua_State *L, lua_Hook func, int mask, int count) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API void (lua_setdummyhook) (lua_State *L, int mask, int count) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API void (lua_appendhook) (lua_State *L, lua_Hook func, int mask, int count) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API void (lua_appenddummyhook) (lua_State *L, int mask, int count) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API void (lua_cleardummyhook) (lua_State *L, int mask, int count) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API lua_Hook (lua_gethook) (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API int (lua_gethookmask) (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API int (lua_gethookcount) (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;

LUA_API int (db_swinterruptdefined) (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;
LUA_API int (db_callswinterruptdirect) (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;

LUA_API int (lua_setcstacklimit) (lua_State *L, unsigned int limit) ATTRIB_F1CODE_BUILDSWITCH;

struct lua_Debug {
  int event;
  const char *name;	/* (n) */
  const char *namewhat;	/* (n) 'global', 'local', 'field', 'method' */
  const char *what;	/* (S) 'Lua', 'C', 'main', 'tail' */
  const char *source;	/* (S) */
  size_t srclen;	/* (S) */
  int currentline;	/* (l) */
  int linedefined;	/* (S) */
  int lastlinedefined;	/* (S) */
  unsigned char nups;	/* (u) number of upvalues */
  unsigned char nparams;/* (u) number of parameters */
  char isvararg;        /* (u) */
  char istailcall;	/* (t) */
  unsigned short ftransfer;   /* (r) index of first value transferred */
  unsigned short ntransfer;   /* (r) number of transferred values */
  char short_src[LUA_IDSIZE]; /* (S) */
  /* private part */
  struct CallInfo *i_ci;  /* active function */
};

void l_message (const char *pname, const char *msg) ATTRIB_F1CODE_BUILDSWITCH;
int report (lua_State *L, int status) ATTRIB_F1CODE_BUILDSWITCH;
int msghandler (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;
int docall (lua_State *L, int narg, int nres) ATTRIB_F1CODE_BUILDSWITCH;
void print_version (void) ATTRIB_F1CODE_BUILDSWITCH;
void createargtable (lua_State *L, char **argv, int argc, int script) ATTRIB_F1CODE_BUILDSWITCH;
int dochunk (lua_State *L, int status) ATTRIB_F1CODE_BUILDSWITCH;
int dofile (lua_State *L, const char *name) ATTRIB_F1CODE_BUILDSWITCH;
int dostring (lua_State *L, const char *s, const char *name) ATTRIB_F1CODE_BUILDSWITCH;
int pushargs (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;
int handle_luainit (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;
const char *get_prompt (lua_State *L, int firstline) ATTRIB_F1CODE_BUILDSWITCH;
int incomplete (lua_State *L, int status) ATTRIB_F1CODE_BUILDSWITCH;
int lua_saveline (lua_State *L, const char *line) ATTRIB_F1CODE_BUILDSWITCH;
int pushline (lua_State *L, int firstline, int permitusercommands) ATTRIB_F1CODE_BUILDSWITCH;
int addreturn (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;
int multiline (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;
int loadline (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;
void l_print (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;
void doREPL (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;

/* }====================================================================== */


/******************************************************************************
* Copyright (C) 1994-2023 Lua.org, PUC-Rio.
*
* Permission is hereby granted, free of charge, to any person obtaining
* a copy of this software and associated documentation files (the
* "Software"), to deal in the Software without restriction, including
* without limitation the rights to use, copy, modify, merge, publish,
* distribute, sublicense, and/or sell copies of the Software, and to
* permit persons to whom the Software is furnished to do so, subject to
* the following conditions:
*
* The above copyright notice and this permission notice shall be
* included in all copies or substantial portions of the Software.
*
* THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
* EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
* MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
* IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
* CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
* TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
* SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
******************************************************************************/

#endif
