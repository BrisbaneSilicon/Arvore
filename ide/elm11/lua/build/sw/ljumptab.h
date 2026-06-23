/*
** $Id: ljumptab.h $
** Jump Table for the Lua interpreter
** See Copyright Notice in lua.h
*/

#ifndef ljumptab_h
#define ljumptab_h

#include "lvm.h"
#include "ldebug.h"
#include "global.h"
#include "config.h"
#include "lopcodes.h"

#undef vmdispatch
#undef vmcase
#undef vmbreak

#ifdef DEBUG_VPRINT_LVM_DISPATCH
    #define vmdispatch() {                                                              \
        char c;                                                                         \
                                                                                        \
        while(1) {                                                                      \
            c = uart_read_char_blocking();                                              \
            if(c == 'c') {                                                              \
                uart_write_string("[CI ADDR] 0x");                                      \
                uart_write_hexidecimal((uint32_t)ci, 8);                                \
                uart_write_string(STR_NL_CR);                                           \
            } else if(c == 'i') {                                                       \
                uart_write_string("[INST] 0x");                                         \
                uart_write_hexidecimal((uint32_t)VM.inst, 8);                          \
                uart_write_string(STR_NL_CR);                                           \
            } else if(c == 'k') {                                                       \
                c = uart_read_char_blocking();                                          \
                if(c == 'b') {                                                          \
                    uart_write_string("[CONST B] dump"STR_NL_CR STR_NL_CR);             \
                    luaG_dumpTValue((TValue *)KB(VM.inst));                            \
                } else if(c == 'c') {                                                   \
                    uart_write_string("[CONST C] dump"STR_NL_CR STR_NL_CR);             \
                    luaG_dumpTValue((TValue *)KC(VM.inst));                            \
                }                                                                       \
            } else if(c == 'l') {                                                       \
                uart_write_string("[DEBUG] lua line: ");                                \
                uart_write_uint32_t(luaG_getfuncline(cl->p, pcRel(VM.pc, cl->p)));     \
                uart_write_string(STR_NL_CR);                                           \
            } else if(c == 'p') {                                                       \
                uart_write_string("[PC] 0x");                                           \
                uart_write_hexidecimal((uint32_t)VM.pc, 8);                            \
                uart_write_string(STR_NL_CR);                                           \
            } else if(c == 'r') {                                                       \
                c = uart_read_char_blocking();                                          \
                if(c == 'a') {                                                          \
                    uart_write_string("[REG A] dump"STR_NL_CR STR_NL_CR);               \
                    luaG_dumpStkId(RA(VM.inst));                                       \
                } else if(c == 'b') {                                                   \
                    uart_write_string("[REG B] dump"STR_NL_CR STR_NL_CR);               \
                    luaG_dumpStkId(RB(VM.inst));                                       \
                } else if(c == 'c') {                                                   \
                    uart_write_string("[REG C] dump"STR_NL_CR STR_NL_CR);               \
                    luaG_dumpStkId(RC(VM.inst));                                       \
                }                                                                       \
            } else if(c == 's') {                                                       \
                luaG_dumpstate(L, VM);                                                  \
            } else if(c == 't') {                                                       \
                print_cpu_access_trace();                                               \
            } else {                                                                    \
                break;                                                                  \
            }                                                                           \
        }                                                                               \
                                                                                        \
        goto *disptab[GET_OPCODE(VM.inst)];                                            \
    }

#else
    #ifdef DEBUG_VPRINT_CPU_ACCESS
        #define vmdispatch() *LVM = (uint32_t)(&VM); print_cpu_access_trace(); goto *disptab[GET_OPCODE(VM.inst)];
    #else
        #define vmdispatch() *LVM = (uint32_t)(&VM); goto *disptab[GET_OPCODE(VM.inst)];
    #endif

#endif



#define vmcase(l)       L_##l:
#define vmbreak         vmfetch(); vmdispatch();






static const void *const disptab[NUM_OPCODES] = {

#if 0
** you can update the following list with this command:
**
**  sed -n '/^OP_/\!d; s/OP_/\&\&L_OP_/ ; s/,.*/,/ ; s/\/.*// ; p'  lopcodes.h
**
#endif

&&L_OP_MOVE,
&&L_OP_LOADI,
&&L_OP_LOADF,
&&L_OP_LOADK,
&&L_OP_LOADKX,
&&L_OP_LOADFALSE,
&&L_OP_LFALSESKIP,
&&L_OP_LOADTRUE,
&&L_OP_LOADNIL,
&&L_OP_GETUPVAL,
&&L_OP_SETUPVAL,
&&L_OP_GETTABUP,
&&L_OP_GETTABLE,
&&L_OP_GETI,
&&L_OP_GETFIELD,
&&L_OP_SETTABUP,
&&L_OP_SETTABLE,
&&L_OP_SETI,
&&L_OP_SETFIELD,
&&L_OP_NEWTABLE,
&&L_OP_SELF,
&&L_OP_ADDI,
&&L_OP_ADDK,
&&L_OP_SUBK,
&&L_OP_MULK,
&&L_OP_MODK,
&&L_OP_POWK,
&&L_OP_DIVK,
&&L_OP_IDIVK,
&&L_OP_BANDK,
&&L_OP_BORK,
&&L_OP_BXORK,
&&L_OP_SHRI,
&&L_OP_SHLI,
&&L_OP_ADD,
&&L_OP_SUB,
&&L_OP_MUL,
&&L_OP_MOD,
&&L_OP_POW,
&&L_OP_DIV,
&&L_OP_IDIV,
&&L_OP_BAND,
&&L_OP_BOR,
&&L_OP_BXOR,
&&L_OP_SHL,
&&L_OP_SHR,
&&L_OP_MMBIN,
&&L_OP_MMBINI,
&&L_OP_MMBINK,
&&L_OP_UNM,
&&L_OP_BNOT,
&&L_OP_NOT,
&&L_OP_LEN,
&&L_OP_CONCAT,
&&L_OP_CLOSE,
&&L_OP_TBC,
&&L_OP_JMP,
&&L_OP_EQ,
&&L_OP_LT,
&&L_OP_LE,
&&L_OP_EQK,
&&L_OP_EQI,
&&L_OP_LTI,
&&L_OP_LEI,
&&L_OP_GTI,
&&L_OP_GEI,
&&L_OP_TEST,
&&L_OP_TESTSET,
&&L_OP_CALL,
&&L_OP_TAILCALL,
&&L_OP_RETURN,
&&L_OP_RETURN0,
&&L_OP_RETURN1,
&&L_OP_FORLOOP,
&&L_OP_FORPREP,
&&L_OP_TFORPREP,
&&L_OP_TFORCALL,
&&L_OP_TFORLOOP,
&&L_OP_SETLIST,
&&L_OP_CLOSURE,
&&L_OP_VARARG,
&&L_OP_VARARGPREP,
&&L_OP_EXTRAARG

};

#endif