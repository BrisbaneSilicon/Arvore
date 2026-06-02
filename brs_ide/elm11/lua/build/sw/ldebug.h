/*
** $Id: ldebug.h $
** Auxiliary functions from Debug Interface module
** See Copyright Notice in lua.h
*/

#ifndef ldebug_h
#define ldebug_h


#include "lstate.h"
#include "lauxlib.h"

#define pcRel(pc, p)	(cast_int((pc) - (p)->code) - 1)


/* Active Lua function (given call info) */
#define ci_func(ci)		(clLvalue(s2v((ci)->func.p)))


#define resethookcount(L)	(L->hookcount = L->basehookcount)

/*
** mark for entries in 'lineinfo' array that has absolute information in
** 'abslineinfo' array
*/
#define ABSLINEINFO	(-0x80)


/*
** MAXimum number of successive Instructions WiTHout ABSolute line
** information. (A power of two allows fast divisions.)
*/
#if !defined(MAXIWTHABS)
#define MAXIWTHABS	128
#endif

LUAI_FUNC int luaG_traceexec (lua_State *L, volatile const Instruction* volatile pc) ATTRIB_RUNTIMECODE;


LUAI_FUNC int luaG_getfuncline (const Proto *f, int pc) ATTRIB_F1CODE_BUILDSWITCH;
LUAI_FUNC const char *luaG_findlocal (lua_State *L, CallInfo *ci, int n,
                                                    StkId *pos) ATTRIB_F1CODE_BUILDSWITCH;
LUAI_FUNC l_noret luaG_typeerror (lua_State *L, const TValue *o,
                                                const char *opname) ATTRIB_F1CODE_BUILDSWITCH;
LUAI_FUNC l_noret luaG_callerror (lua_State *L, const TValue *o) ATTRIB_F1CODE_BUILDSWITCH;
LUAI_FUNC l_noret luaG_forerror (lua_State *L, const TValue *o,
                                               const char *what) ATTRIB_F1CODE_BUILDSWITCH;
LUAI_FUNC l_noret luaG_concaterror (lua_State *L, const TValue *p1,
                                                  const TValue *p2) ATTRIB_F1CODE_BUILDSWITCH;
LUAI_FUNC l_noret luaG_opinterror (lua_State *L, const TValue *p1,
                                                 const TValue *p2,
                                                 const char *msg) ATTRIB_F1CODE_BUILDSWITCH;
LUAI_FUNC l_noret luaG_tointerror (lua_State *L, const TValue *p1,
                                                 const TValue *p2) ATTRIB_F1CODE_BUILDSWITCH;
LUAI_FUNC l_noret luaG_ordererror (lua_State *L, const TValue *p1,
                                                 const TValue *p2) ATTRIB_F1CODE_BUILDSWITCH;
LUAI_FUNC l_noret luaG_runerror (lua_State *L, const char *fmt, ...) ATTRIB_F1CODE_BUILDSWITCH;
LUAI_FUNC const char *luaG_addinfo (lua_State *L, const char *msg,
                                                  TString *src, int line) ATTRIB_F1CODE_BUILDSWITCH;
LUAI_FUNC l_noret luaG_errormsg (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;
LUAI_FUNC l_noret luaG_exitprogramerrormsg (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;

LUAI_FUNC void luaG_dumpstack (lua_State *L, int level) ATTRIB_F1CODE_BUILDSWITCH;

LUAI_FUNC void luaG_dumpstate (lua_State *L, lvm_State VM) ATTRIB_F1CODE_BUILDSWITCH;

LUAI_FUNC uint8_t luaG_dumpTValue (TValue *tvalue) ATTRIB_F1CODE_BUILDSWITCH;
LUAI_FUNC void luaG_dumpStkId (StkId s) ATTRIB_F1CODE_BUILDSWITCH;

LUAI_FUNC void luaG_dumpLVMState(lvm_State VM) ATTRIB_F1CODE_BUILDSWITCH;

#endif
