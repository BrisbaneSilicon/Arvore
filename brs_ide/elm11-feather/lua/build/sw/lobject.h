/*
** $Id: lobject.h $
** Type definitions for Lua objects
** See Copyright Notice in lua.h
*/


#ifndef lobject_h
#define lobject_h


#include <stdarg.h>

#include "config.h"

#include "llimits.h"
#include "io.h"
#include "interrupt.h"


/*
** Extra types for collectable non-values
*/
#define LUA_TUPVAL	LUA_NUMTYPES  /* upvalues */
#define LUA_TPROTO	(LUA_NUMTYPES+1)  /* function prototypes */
#define LUA_TDEADKEY	(LUA_NUMTYPES+2)  /* removed keys in tables */



/*
** number of all possible types (including LUA_TNONE but excluding DEADKEY)
*/
#define LUA_TOTALTYPES		(LUA_TPROTO + 2)


/*
** tags for Tagged Values have the following use of bits:
** bits 0-3: actual tag (a LUA_T* constant)
** bits 4-5: variant bits
** bit 6: whether value is collectable
*/

/* add variant bits to a type */
#define makevariant(t,v)	((t) | ((v) << 8))



/*
** Union of all Lua values
*/
typedef union Value {
  struct GCObject *gc;    /* collectable objects */
  void *p;         /* light userdata */
  lua_CFunction f; /* light C functions */
  lua_Integer i;   /* integer numbers */
  lua_Number n;    /* float numbers */
  /* not used, but may avoid warnings for uninitialized value */
  lu_byte ub;
} Value;


/*
** Tagged Values. This is the basic representation of values in Lua:
** an actual value plus a tag with its type.
*/

#define TValuefields	Value value_; lu_short tt_

typedef struct TValue {
  TValuefields;
} TValue;


#define val_(o)		((o)->value_)
#define valraw(o)	(val_(o))


/* raw type tag of a TValue */
#define rawtt(o)	((o)->tt_)

/* tag with no variants (bits 0-5) */
#define novariant(t)	((t) & 0x3F)

/* type tag of a TValue (bits 0-5 for tags + variant bits 8-15) */
#define withvariant(t)	((t) & 0xFF3F)
#define ttypetag(o)	withvariant(rawtt(o))

/* type of a TValue */
#define ttype(o)	(novariant(rawtt(o)))


/* Macros to test type */
#define checktag(o,t)		(rawtt(o) == (t))
#define checktype(o,t)		(ttype(o) == (t))


/* Macros for internal tests */

/* collectable object has the same tag as the original value */
#define righttt(obj)		(ttypetag(obj) == gcvalue(obj)->tt)

/*
** Any value being manipulated by the program either is non
** collectable, or the collectable object has the right tag
** and it is not dead. The option 'L == NULL' allows other
** macros using this one to be used where L is not available.
*/
#define checkliveness(L,obj) \
	((void)L, lua_longassert(!iscollectable(obj) || \
		(righttt(obj) && (L == NULL || !isdead(G(L),gcvalue(obj))))))


/* Macros to set values */

/* set a value's tag */
#define settt_(o,t)	((o)->tt_=(t))


/* main macro to copy values (from 'obj2' to 'obj1') */
#define setobj(L,obj1,obj2) \
	{ TValue *io1=(obj1); const TValue *io2=(obj2); \
          io1->value_ = io2->value_; settt_(io1, io2->tt_); \
	  checkliveness(L,io1); lua_assert(!isnonstrictnil(io1)); }

/*
** Different types of assignments, according to source and destination.
** (They are mostly equal now, but may be different in the future.)
*/

/* from stack to stack */
#define setobjs2s(L,o1,o2)	setobj(L,s2v(o1),s2v(o2))
/* to stack (not from same stack) */
#define setobj2s(L,o1,o2)	setobj(L,s2v(o1),o2)
/* from table to same table */
#define setobjt2t	setobj
/* to new object */
#define setobj2n	setobj
/* to table */
#define setobj2t	setobj


/*
** Entries in a Lua stack. Field 'tbclist' forms a list of all
** to-be-closed variables active in this stack. Dummy entries are
** used when the distance between two tbc variables does not fit
** in an unsigned short. They are represented by delta==0, and
** their real delta is always the maximum value that fits in
** that field.
*/
typedef union StackValue {
  TValue val;
  struct {
    TValuefields;
    unsigned short delta;
  } tbclist;
} StackValue;


/* index to stack elements */
typedef StackValue *StkId;


/*
** When reallocating the stack, change all pointers to the stack into
** proper offsets.
*/
typedef union {
  StkId p;  /* actual pointer */
  ptrdiff_t offset;  /* used while the stack is being reallocated */
} StkIdRel;


/* convert a 'StackValue' to a 'TValue' */
#define s2v(o)	(&(o)->val)



/*
** {==================================================================
** Nil
** ===================================================================
*/

/* Standard nil */
#define LUA_VNIL	makevariant(LUA_TNIL, 0)

/* Empty slot (which might be different from a slot containing nil) */
#define LUA_VEMPTY	makevariant(LUA_TNIL, 1)

/* Value returned for a key not found in a table (absent key) */
#define LUA_VABSTKEY	makevariant(LUA_TNIL, 2)


/* macro to test for (any kind of) nil */
#define ttisnil(v)		checktype((v), LUA_TNIL)


/* macro to test for a standard nil */
#define ttisstrictnil(o)	checktag((o), LUA_VNIL)


#define setnilvalue(obj) settt_(obj, LUA_VNIL)


#define isabstkey(v)		checktag((v), LUA_VABSTKEY)


/*
** macro to detect non-standard nils (used only in assertions)
*/
#define isnonstrictnil(v)	(ttisnil(v) && !ttisstrictnil(v))


/*
** By default, entries with any kind of nil are considered empty.
** (In any definition, values associated with absent keys must also
** be accepted as empty.)
*/
#define isempty(v)		ttisnil(v)


/* macro defining a value corresponding to an absent key */
#define ABSTKEYCONSTANT		{NULL}, LUA_VABSTKEY


/* mark an entry as empty */
#define setempty(v)		settt_(v, LUA_VEMPTY)



/* }================================================================== */


/*
** {==================================================================
** Booleans
** ===================================================================
*/


#define LUA_VFALSE	makevariant(LUA_TBOOLEAN, 0)
#define LUA_VTRUE	makevariant(LUA_TBOOLEAN, 1)

#define ttisboolean(o)		checktype((o), LUA_TBOOLEAN)
#define ttisfalse(o)		checktag((o), LUA_VFALSE)
#define ttistrue(o)		checktag((o), LUA_VTRUE)


#define l_isfalse(o)	(ttisfalse(o) || ttisnil(o))


#define setbfvalue(obj)		settt_(obj, LUA_VFALSE)
#define setbtvalue(obj)		settt_(obj, LUA_VTRUE)

/* }================================================================== */

/*
** {==================================================================
** embLua Types
** ===================================================================
*/

#define LUA_VLOW                                makevariant(LUA_TDWEEZLE_GPIO, 0)
#define LUA_VHIGH                               makevariant(LUA_TDWEEZLE_GPIO, 1)
#define LUA_VTOGGLE                             makevariant(LUA_TDWEEZLE_GPIO, 2)

#define ttisdweezlegpio(o)                      checktype((o), LUA_TDWEEZLE_GPIO)
#define ttislow(o)                              checktag((o), LUA_VLOW)
#define ttishigh(o)                             checktag((o), LUA_VHIGH)
#define ttistoggle(o)                           checktag((o), LUA_VTOGGLE)
#define setdwzllowvalue(obj)                    settt_(obj, LUA_VLOW)
#define setdwzlhighvalue(obj)                   settt_(obj, LUA_VHIGH)
#define setdwzltogglevalue(obj)                 settt_(obj, LUA_VTOGGLE)

#define LUA_VPIN1                               makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 0) // NOTE: see 'setdwzlpinvalue' if modifying
#define LUA_VPIN2                               makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 1)
#define LUA_VPIN3                               makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 2)
#define LUA_VPIN4                               makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 3)
#define LUA_VPIN5                               makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 4)
#define LUA_VPIN6                               makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 5)
#define LUA_VPIN7                               makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 6)
#define LUA_VPIN8                               makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 7)
#define LUA_VPIN9                               makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 8)
#define LUA_VPIN10                              makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 9)
#define LUA_VPIN11                              makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 10)
#define LUA_VPIN12                              makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 11)
#define LUA_VPIN13                              makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 12)
#define LUA_VPIN14                              makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 13)
#define LUA_VPIN15                              makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 14)
#define LUA_VPIN16                              makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 15)
#define LUA_VPIN17                              makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 16)
#define LUA_VPIN18                              makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 17)
#define LUA_VPIN19                              makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 18)
#define LUA_VPIN20                              makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 19)
#define LUA_VPIN21                              makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 20)
#define LUA_VPIN22                              makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 21)
#define LUA_VPIN23                              makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 22)
#define LUA_VPIN24                              makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 23)
#define LUA_VPIN25                              makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 24)
#define LUA_VPIN26                              makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 25)
#define LUA_VPIN27                              makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 26)
#define LUA_VPIN28                              makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 27)
#define LUA_VPIN29                              makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 28)
#define LUA_VPIN30                              makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 29)
#define LUA_VPIN31                              makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 30)
#define LUA_VPIN32                              makevariant(LUA_TDWEEZLE_DIGITAL_PIN, 31)

#define ttisdweezlepin(o)                       checktype((o), LUA_TDWEEZLE_DIGITAL_PIN)
#define ttispin1(o)                             checktag((o), LUA_VPIN1)
#define ttispin2(o)                             checktag((o), LUA_VPIN2)
#define ttispin3(o)                             checktag((o), LUA_VPIN3)
#define ttispin4(o)                             checktag((o), LUA_VPIN4)
#define ttispin5(o)                             checktag((o), LUA_VPIN5)
#define ttispin6(o)                             checktag((o), LUA_VPIN6)
#define ttispin7(o)                             checktag((o), LUA_VPIN7)
#define ttispin8(o)                             checktag((o), LUA_VPIN8)
#define ttispin9(o)                             checktag((o), LUA_VPIN9)
#define ttispin10(o)                            checktag((o), LUA_VPIN10)
#define ttispin11(o)                            checktag((o), LUA_VPIN11)
#define ttispin12(o)                            checktag((o), LUA_VPIN12)
#define ttispin13(o)                            checktag((o), LUA_VPIN13)
#define ttispin14(o)                            checktag((o), LUA_VPIN14)
#define ttispin15(o)                            checktag((o), LUA_VPIN15)
#define ttispin16(o)                            checktag((o), LUA_VPIN16)
#define ttispin17(o)                            checktag((o), LUA_VPIN17)
#define ttispin18(o)                            checktag((o), LUA_VPIN18)
#define ttispin19(o)                            checktag((o), LUA_VPIN19)
#define ttispin20(o)                            checktag((o), LUA_VPIN20)
#define ttispin21(o)                            checktag((o), LUA_VPIN21)
#define ttispin22(o)                            checktag((o), LUA_VPIN22)
#define ttispin23(o)                            checktag((o), LUA_VPIN23)
#define ttispin24(o)                            checktag((o), LUA_VPIN24)
#define ttispin25(o)                            checktag((o), LUA_VPIN25)
#define ttispin26(o)                            checktag((o), LUA_VPIN26)
#define ttispin27(o)                            checktag((o), LUA_VPIN27)
#define ttispin28(o)                            checktag((o), LUA_VPIN28)
#define ttispin29(o)                            checktag((o), LUA_VPIN29)
#define ttispin30(o)                            checktag((o), LUA_VPIN30)
#define ttispin31(o)                            checktag((o), LUA_VPIN31)
#define ttispin32(o)                            checktag((o), LUA_VPIN32)

#define setdwzlpin1value(obj)                   settt_(obj, LUA_VPIN1)
#define setdwzlpin2value(obj)                   settt_(obj, LUA_VPIN2)
#define setdwzlpin3value(obj)                   settt_(obj, LUA_VPIN3)
#define setdwzlpin4value(obj)                   settt_(obj, LUA_VPIN4)
#define setdwzlpin5value(obj)                   settt_(obj, LUA_VPIN5)
#define setdwzlpin6value(obj)                   settt_(obj, LUA_VPIN6)
#define setdwzlpin7value(obj)                   settt_(obj, LUA_VPIN7)
#define setdwzlpin8value(obj)                   settt_(obj, LUA_VPIN8)
#define setdwzlpin9value(obj)                   settt_(obj, LUA_VPIN9)
#define setdwzlpin10value(obj)                  settt_(obj, LUA_VPIN10)
#define setdwzlpin11value(obj)                  settt_(obj, LUA_VPIN11)
#define setdwzlpin12value(obj)                  settt_(obj, LUA_VPIN12)
#define setdwzlpin13value(obj)                  settt_(obj, LUA_VPIN13)
#define setdwzlpin14value(obj)                  settt_(obj, LUA_VPIN14)
#define setdwzlpin15value(obj)                  settt_(obj, LUA_VPIN15)
#define setdwzlpin16value(obj)                  settt_(obj, LUA_VPIN16)
#define setdwzlpin17value(obj)                  settt_(obj, LUA_VPIN17)
#define setdwzlpin18value(obj)                  settt_(obj, LUA_VPIN18)
#define setdwzlpin19value(obj)                  settt_(obj, LUA_VPIN19)
#define setdwzlpin20value(obj)                  settt_(obj, LUA_VPIN20)
#define setdwzlpin21value(obj)                  settt_(obj, LUA_VPIN21)
#define setdwzlpin22value(obj)                  settt_(obj, LUA_VPIN22)
#define setdwzlpin23value(obj)                  settt_(obj, LUA_VPIN23)
#define setdwzlpin24value(obj)                  settt_(obj, LUA_VPIN24)
#define setdwzlpin25value(obj)                  settt_(obj, LUA_VPIN25)
#define setdwzlpin26value(obj)                  settt_(obj, LUA_VPIN26)
#define setdwzlpin27value(obj)                  settt_(obj, LUA_VPIN27)
#define setdwzlpin28value(obj)                  settt_(obj, LUA_VPIN28)
#define setdwzlpin29value(obj)                  settt_(obj, LUA_VPIN29)
#define setdwzlpin30value(obj)                  settt_(obj, LUA_VPIN30)
#define setdwzlpin31value(obj)                  settt_(obj, LUA_VPIN31)
#define setdwzlpin32value(obj)                  settt_(obj, LUA_VPIN32)

#define LUA_VPIN1_BITMASK                       makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 0)
#define LUA_VPIN2_BITMASK                       makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 1)
#define LUA_VPIN3_BITMASK                       makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 2)
#define LUA_VPIN4_BITMASK                       makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 3)
#define LUA_VPIN5_BITMASK                       makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 4)
#define LUA_VPIN6_BITMASK                       makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 5)
#define LUA_VPIN7_BITMASK                       makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 6)
#define LUA_VPIN8_BITMASK                       makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 7)
#define LUA_VPIN9_BITMASK                       makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 8)
#define LUA_VPIN10_BITMASK                      makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 9)
#define LUA_VPIN11_BITMASK                      makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 10)
#define LUA_VPIN12_BITMASK                      makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 11)
#define LUA_VPIN13_BITMASK                      makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 12)
#define LUA_VPIN14_BITMASK                      makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 13)
#define LUA_VPIN15_BITMASK                      makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 14)
#define LUA_VPIN16_BITMASK                      makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 15)
#define LUA_VPIN17_BITMASK                      makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 16)
#define LUA_VPIN18_BITMASK                      makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 17)
#define LUA_VPIN19_BITMASK                      makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 18)
#define LUA_VPIN20_BITMASK                      makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 19)
#define LUA_VPIN21_BITMASK                      makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 20)
#define LUA_VPIN22_BITMASK                      makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 21)
#define LUA_VPIN23_BITMASK                      makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 22)
#define LUA_VPIN24_BITMASK                      makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 23)
#define LUA_VPIN25_BITMASK                      makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 24)
#define LUA_VPIN26_BITMASK                      makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 25)
#define LUA_VPIN27_BITMASK                      makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 26)
#define LUA_VPIN28_BITMASK                      makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 27)
#define LUA_VPIN29_BITMASK                      makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 28)
#define LUA_VPIN30_BITMASK                      makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 29)
#define LUA_VPIN31_BITMASK                      makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 30)
#define LUA_VPIN32_BITMASK                      makevariant(LUA_TDWEEZLE_DIGITAL_PIN_BITMASK, 31)

#define ttisdweezlepinbitmask(o)                checktype((o), LUA_TDWEEZLE_DIGITAL_PIN_BITMASK)
#define ttispin1bitmask(o)                      checktag((o), LUA_VPIN1_BITMASK)
#define ttispin2bitmask(o)                      checktag((o), LUA_VPIN2_BITMASK)
#define ttispin3bitmask(o)                      checktag((o), LUA_VPIN3_BITMASK)
#define ttispin4bitmask(o)                      checktag((o), LUA_VPIN4_BITMASK)
#define ttispin5bitmask(o)                      checktag((o), LUA_VPIN5_BITMASK)
#define ttispin6bitmask(o)                      checktag((o), LUA_VPIN6_BITMASK)
#define ttispin7bitmask(o)                      checktag((o), LUA_VPIN7_BITMASK)
#define ttispin8bitmask(o)                      checktag((o), LUA_VPIN8_BITMASK)
#define ttispin9bitmask(o)                      checktag((o), LUA_VPIN9_BITMASK)
#define ttispin10bitmask(o)                     checktag((o), LUA_VPIN10_BITMASK)
#define ttispin11bitmask(o)                     checktag((o), LUA_VPIN11_BITMASK)
#define ttispin12bitmask(o)                     checktag((o), LUA_VPIN12_BITMASK)
#define ttispin13bitmask(o)                     checktag((o), LUA_VPIN13_BITMASK)
#define ttispin14bitmask(o)                     checktag((o), LUA_VPIN14_BITMASK)
#define ttispin15bitmask(o)                     checktag((o), LUA_VPIN15_BITMASK)
#define ttispin16bitmask(o)                     checktag((o), LUA_VPIN16_BITMASK)
#define ttispin17bitmask(o)                     checktag((o), LUA_VPIN17_BITMASK)
#define ttispin18bitmask(o)                     checktag((o), LUA_VPIN18_BITMASK)
#define ttispin19bitmask(o)                     checktag((o), LUA_VPIN19_BITMASK)
#define ttispin20bitmask(o)                     checktag((o), LUA_VPIN20_BITMASK)
#define ttispin21bitmask(o)                     checktag((o), LUA_VPIN21_BITMASK)
#define ttispin22bitmask(o)                     checktag((o), LUA_VPIN22_BITMASK)
#define ttispin23bitmask(o)                     checktag((o), LUA_VPIN23_BITMASK)
#define ttispin24bitmask(o)                     checktag((o), LUA_VPIN24_BITMASK)
#define ttispin25bitmask(o)                     checktag((o), LUA_VPIN25_BITMASK)
#define ttispin26bitmask(o)                     checktag((o), LUA_VPIN26_BITMASK)
#define ttispin27bitmask(o)                     checktag((o), LUA_VPIN27_BITMASK)
#define ttispin28bitmask(o)                     checktag((o), LUA_VPIN28_BITMASK)
#define ttispin29bitmask(o)                     checktag((o), LUA_VPIN29_BITMASK)
#define ttispin30bitmask(o)                     checktag((o), LUA_VPIN30_BITMASK)
#define ttispin31bitmask(o)                     checktag((o), LUA_VPIN31_BITMASK)
#define ttispin32bitmask(o)                     checktag((o), LUA_VPIN32_BITMASK)
#define setdwzlpin1bitmaskvalue(obj)            settt_(obj, LUA_VPIN1_BITMASK)
#define setdwzlpin2bitmaskvalue(obj)            settt_(obj, LUA_VPIN2_BITMASK)
#define setdwzlpin3bitmaskvalue(obj)            settt_(obj, LUA_VPIN3_BITMASK)
#define setdwzlpin4bitmaskvalue(obj)            settt_(obj, LUA_VPIN4_BITMASK)
#define setdwzlpin5bitmaskvalue(obj)            settt_(obj, LUA_VPIN5_BITMASK)
#define setdwzlpin6bitmaskvalue(obj)            settt_(obj, LUA_VPIN6_BITMASK)
#define setdwzlpin7bitmaskvalue(obj)            settt_(obj, LUA_VPIN7_BITMASK)
#define setdwzlpin8bitmaskvalue(obj)            settt_(obj, LUA_VPIN8_BITMASK)
#define setdwzlpin9bitmaskvalue(obj)            settt_(obj, LUA_VPIN9_BITMASK)
#define setdwzlpin10bitmaskvalue(obj)           settt_(obj, LUA_VPIN10_BITMASK)
#define setdwzlpin11bitmaskvalue(obj)           settt_(obj, LUA_VPIN11_BITMASK)
#define setdwzlpin12bitmaskvalue(obj)           settt_(obj, LUA_VPIN12_BITMASK)
#define setdwzlpin13bitmaskvalue(obj)           settt_(obj, LUA_VPIN13_BITMASK)
#define setdwzlpin14bitmaskvalue(obj)           settt_(obj, LUA_VPIN14_BITMASK)
#define setdwzlpin15bitmaskvalue(obj)           settt_(obj, LUA_VPIN15_BITMASK)
#define setdwzlpin16bitmaskvalue(obj)           settt_(obj, LUA_VPIN16_BITMASK)
#define setdwzlpin17bitmaskvalue(obj)           settt_(obj, LUA_VPIN17_BITMASK)
#define setdwzlpin18bitmaskvalue(obj)           settt_(obj, LUA_VPIN18_BITMASK)
#define setdwzlpin19bitmaskvalue(obj)           settt_(obj, LUA_VPIN19_BITMASK)
#define setdwzlpin20bitmaskvalue(obj)           settt_(obj, LUA_VPIN20_BITMASK)
#define setdwzlpin21bitmaskvalue(obj)           settt_(obj, LUA_VPIN21_BITMASK)
#define setdwzlpin22bitmaskvalue(obj)           settt_(obj, LUA_VPIN22_BITMASK)
#define setdwzlpin23bitmaskvalue(obj)           settt_(obj, LUA_VPIN23_BITMASK)
#define setdwzlpin24bitmaskvalue(obj)           settt_(obj, LUA_VPIN24_BITMASK)
#define setdwzlpin25bitmaskvalue(obj)           settt_(obj, LUA_VPIN25_BITMASK)
#define setdwzlpin26bitmaskvalue(obj)           settt_(obj, LUA_VPIN26_BITMASK)
#define setdwzlpin27bitmaskvalue(obj)           settt_(obj, LUA_VPIN27_BITMASK)
#define setdwzlpin28bitmaskvalue(obj)           settt_(obj, LUA_VPIN28_BITMASK)
#define setdwzlpin29bitmaskvalue(obj)           settt_(obj, LUA_VPIN29_BITMASK)
#define setdwzlpin30bitmaskvalue(obj)           settt_(obj, LUA_VPIN30_BITMASK)
#define setdwzlpin31bitmaskvalue(obj)           settt_(obj, LUA_VPIN31_BITMASK)
#define setdwzlpin32bitmaskvalue(obj)           settt_(obj, LUA_VPIN32_BITMASK)

#define LUA_VIO_TYPE_NONE                       makevariant(LUA_TDWEEZLE_DIGITAL_PIN_TYPE, 0)
#define LUA_VIO_TYPE_GPIO_OUT                   makevariant(LUA_TDWEEZLE_DIGITAL_PIN_TYPE, 1)
#define LUA_VIO_TYPE_GPIO_IN                    makevariant(LUA_TDWEEZLE_DIGITAL_PIN_TYPE, 2)
#define LUA_VIO_TYPE_PWM                        makevariant(LUA_TDWEEZLE_DIGITAL_PIN_TYPE, 3)
#define LUA_VIO_TYPE_UART_OUT                   makevariant(LUA_TDWEEZLE_DIGITAL_PIN_TYPE, 4)
#define LUA_VIO_TYPE_UART_IN                    makevariant(LUA_TDWEEZLE_DIGITAL_PIN_TYPE, 5)
#define LUA_VIO_TYPE_SPI_OUT                    makevariant(LUA_TDWEEZLE_DIGITAL_PIN_TYPE, 6)
#define LUA_VIO_TYPE_SPI_IN                     makevariant(LUA_TDWEEZLE_DIGITAL_PIN_TYPE, 7)
#define LUA_VIO_TYPE_I2C                        makevariant(LUA_TDWEEZLE_DIGITAL_PIN_TYPE, 8)

#define ttisdweezleiotype(o)                    checktype((o), LUA_TDWEEZLE_DIGITAL_PIN_TYPE)
#define ttisnone(o)                             checktag((o), LUA_VIO_TYPE_NONE)
#define ttisgpioout(o)                          checktag((o), LUA_VIO_TYPE_GPIO_OUT)
#define ttisgpioin(o)                           checktag((o), LUA_VIO_TYPE_GPIO_IN)
#define ttispwm(o)                              checktag((o), LUA_VIO_TYPE_PWM)
#define ttisuartout(o)                          checktag((o), LUA_VIO_TYPE_UART_OUT)
#define ttisuartin(o)                           checktag((o), LUA_VIO_TYPE_UART_IN)
#define ttisspiout(o)                           checktag((o), LUA_VIO_TYPE_SPI_OUT)
#define ttisspiin(o)                            checktag((o), LUA_VIO_TYPE_SPI_IN)
#define ttisi2c(o)                              checktag((o), LUA_VIO_TYPE_I2C)
#define setdwzlnonevalue(obj)                   settt_((obj), LUA_VIO_TYPE_NONE)
#define setdwzlgpiooutvalue(obj)                settt_((obj), LUA_VIO_TYPE_GPIO_OUT)
#define setdwzlgpioinvalue(obj)                 settt_((obj), LUA_VIO_TYPE_GPIO_IN)
#define setdwzlpwmvalue(obj)                    settt_((obj), LUA_VIO_TYPE_PWM)
#define setdwzluartoutvalue(obj)                settt_((obj), LUA_VIO_TYPE_UART_OUT)
#define setdwzluartinvalue(obj)                 settt_((obj), LUA_VIO_TYPE_UART_IN)
#define setdwzlspioutvalue(obj)                 settt_((obj), LUA_VIO_TYPE_SPI_OUT)
#define setdwzlspiinvalue(obj)                  settt_((obj), LUA_VIO_TYPE_SPI_IN)
#define setdwzli2cvalue(obj)                    settt_((obj), LUA_VIO_TYPE_I2C)

#define LUA_VIO_CTYPE_CORE1                     makevariant(LUA_TDWEEZLE_CORE_TYPE, 1)
#define LUA_VIO_CTYPE_CORE2                     makevariant(LUA_TDWEEZLE_CORE_TYPE, 2)
#define LUA_VIO_CTYPE_CORE3                     makevariant(LUA_TDWEEZLE_CORE_TYPE, 3)
#define LUA_VIO_CTYPE_CORE4                     makevariant(LUA_TDWEEZLE_CORE_TYPE, 4)
#define LUA_VIO_CTYPE_CORE5                     makevariant(LUA_TDWEEZLE_CORE_TYPE, 5)
#define LUA_VIO_CTYPE_CORE6                     makevariant(LUA_TDWEEZLE_CORE_TYPE, 6)
#define LUA_VIO_CTYPE_CORE7                     makevariant(LUA_TDWEEZLE_CORE_TYPE, 7)
#define LUA_VIO_CTYPE_CORE8                     makevariant(LUA_TDWEEZLE_CORE_TYPE, 8)

#define ttisdweezlecoretype(o)                  checktype((o), LUA_TDWEEZLE_CORE_TYPE)
#define ttiscore1(o)                            checktag((o), LUA_VIO_CTYPE_CORE1)
#define ttiscore2(o)                            checktag((o), LUA_VIO_CTYPE_CORE2)
#define ttiscore3(o)                            checktag((o), LUA_VIO_CTYPE_CORE3)
#define ttiscore4(o)                            checktag((o), LUA_VIO_CTYPE_CORE4)
#define ttiscore5(o)                            checktag((o), LUA_VIO_CTYPE_CORE5)
#define ttiscore6(o)                            checktag((o), LUA_VIO_CTYPE_CORE6)
#define ttiscore7(o)                            checktag((o), LUA_VIO_CTYPE_CORE7)
#define ttiscore8(o)                            checktag((o), LUA_VIO_CTYPE_CORE8)
#define setdwzlcore1value(obj)                  settt_((obj), LUA_VIO_CTYPE_CORE1)
#define setdwzlcore2value(obj)                  settt_((obj), LUA_VIO_CTYPE_CORE2)
#define setdwzlcore3value(obj)                  settt_((obj), LUA_VIO_CTYPE_CORE3)
#define setdwzlcore4value(obj)                  settt_((obj), LUA_VIO_CTYPE_CORE4)
#define setdwzlcore5value(obj)                  settt_((obj), LUA_VIO_CTYPE_CORE5)
#define setdwzlcore6value(obj)                  settt_((obj), LUA_VIO_CTYPE_CORE6)
#define setdwzlcore7value(obj)                  settt_((obj), LUA_VIO_CTYPE_CORE7)
#define setdwzlcore8value(obj)                  settt_((obj), LUA_VIO_CTYPE_CORE8)

#define LUA_VGPIO_INTRPT_GND                        makevariant(LUA_TDWEEZLE_DIGITAL_INTERRUPT, 0)
#define LUA_VGPIO_INTRPT_VCC                        makevariant(LUA_TDWEEZLE_DIGITAL_INTERRUPT, 1)
#define LUA_VGPIO_INTRPT_RISING_EDGE                makevariant(LUA_TDWEEZLE_DIGITAL_INTERRUPT, 2)
#define LUA_VGPIO_INTRPT_FALLING_EDGE               makevariant(LUA_TDWEEZLE_DIGITAL_INTERRUPT, 3)
#define LUA_VUART_RX_INTRPT_DATA_AVAILABLE          makevariant(LUA_TDWEEZLE_DIGITAL_INTERRUPT, 4)

#define ttisdweezleinterrupt(o)                     checktype((o), LUA_TDWEEZLE_DIGITAL_INTERRUPT)
#define ttisgpiointrptgnd(o)                        checktag((o), LUA_VGPIO_INTRPT_GND)
#define ttisgpiointrptvcc(o)                        checktag((o), LUA_VGPIO_INTRPT_VCC)
#define ttisgpiointrptrisingedge(o)                 checktag((o), LUA_VGPIO_INTRPT_RISING_EDGE)
#define ttisgpiointrptfallingedge(o)                checktag((o), LUA_VGPIO_INTRPT_FALLING_EDGE)
#define ttisuartrxintrptdataavailable(o)            checktag((o), LUA_VUART_RX_INTRPT_DATA_AVAILABLE)
#define setdwzlgpiointrptgndvalue(obj)              settt_((obj), LUA_VGPIO_INTRPT_GND)
#define setdwzlgpiointrptvccvalue(obj)              settt_((obj), LUA_VGPIO_INTRPT_VCC)
#define setdwzlgpiointrptrisingedgevalue(obj)       settt_((obj), LUA_VGPIO_INTRPT_RISING_EDGE)
#define setdwzlgpiointrptfallingedgevalue(obj)      settt_((obj), LUA_VGPIO_INTRPT_FALLING_EDGE)
#define setdwzluartrxintrptdataavailablevalue(obj)  settt_((obj), LUA_VUART_RX_INTRPT_DATA_AVAILABLE)


/*
** {==================================================================
** Threads
** ===================================================================
*/

#define LUA_VTHREAD		makevariant(LUA_TTHREAD, 0)

#define ttisthread(o)		checktag((o), ctb(LUA_VTHREAD))

#define thvalue(o)	check_exp(ttisthread(o), gco2th(val_(o).gc))

#define setthvalue(L,obj,x) \
  { TValue *io = (obj); lua_State *x_ = (x); \
    val_(io).gc = obj2gco(x_); settt_(io, ctb(LUA_VTHREAD)); \
    checkliveness(L,io); }

#define setthvalue2s(L,o,t)	setthvalue(L,s2v(o),t)

/* }================================================================== */


/*
** {==================================================================
** Collectable Objects
** ===================================================================
*/

/*
** Common Header for all collectable objects (in macro form, to be
** included in other objects)
*/
#define CommonHeader	struct GCObject *next; lu_short tt; lu_byte marked


/* Common type for all collectable objects */
typedef struct GCObject {
  CommonHeader;
} GCObject;


/* Bit mark for collectable types */
#define BIT_ISCOLLECTABLE	(1 << 6)

#define iscollectable(o)	(rawtt(o) & BIT_ISCOLLECTABLE)

/* mark a tag as collectable */
#define ctb(t)			((t) | BIT_ISCOLLECTABLE)

#define gcvalue(o)	check_exp(iscollectable(o), val_(o).gc)

#define gcvalueraw(v)	((v).gc)

#define setgcovalue(L,obj,x) \
  { TValue *io = (obj); GCObject *i_g=(x); \
    val_(io).gc = i_g; settt_(io, ctb(i_g->tt)); }

/* }================================================================== */


/*
** {==================================================================
** Numbers
** ===================================================================
*/

/* Variant tags for numbers */
#define LUA_VNUMINT	makevariant(LUA_TNUMBER, 0)  /* integer numbers */
#define LUA_VNUMFLT	makevariant(LUA_TNUMBER, 1)  /* float numbers */

#define ttisnumber(o)		checktype((o), LUA_TNUMBER)
#define ttisfloat(o)		checktag((o), LUA_VNUMFLT)
#define ttisinteger(o)		checktag((o), LUA_VNUMINT)

#define nvalue(o)	check_exp(ttisnumber(o), \
	(ttisinteger(o) ? cast_num(ivalue(o)) : fltvalue(o)))
#define fltvalue(o)	check_exp(ttisfloat(o), val_(o).n)
#define ivalue(o)	check_exp(ttisinteger(o), val_(o).i)

#define fltvalueraw(v)	((v).n)
#define ivalueraw(v)	((v).i)

#define setfltvalue(obj,x) \
  { TValue *io=(obj); val_(io).n=(x); settt_(io, LUA_VNUMFLT); }

#define chgfltvalue(obj,x) \
  { TValue *io=(obj); lua_assert(ttisfloat(io)); val_(io).n=(x); }

#define setivalue(obj,x) \
  { TValue *io=(obj); val_(io).i=(x); settt_(io, LUA_VNUMINT); }

#define chgivalue(obj,x) \
  { TValue *io=(obj); lua_assert(ttisinteger(io)); val_(io).i=(x); }

/* }================================================================== */


/*
** {==================================================================
** Strings
** ===================================================================
*/

/* Variant tags for strings */
#define LUA_VSHRSTR	makevariant(LUA_TSTRING, 0)  /* short strings */
#define LUA_VLNGSTR	makevariant(LUA_TSTRING, 1)  /* long strings */

#define ttisstring(o)		checktype((o), LUA_TSTRING)
#define ttisshrstring(o)	checktag((o), ctb(LUA_VSHRSTR))
#define ttislngstring(o)	checktag((o), ctb(LUA_VLNGSTR))

#define tsvalueraw(v)	(gco2ts((v).gc))

#define tsvalue(o)	check_exp(ttisstring(o), gco2ts(val_(o).gc))

#define setsvalue(L,obj,x) \
  { TValue *io = (obj); TString *x_ = (x); \
    val_(io).gc = obj2gco(x_); settt_(io, ctb(x_->tt)); \
    checkliveness(L,io); }

/* set a string to the stack */
#define setsvalue2s(L,o,s)	setsvalue(L,s2v(o),s)

/* set a string to a new object */
#define setsvalue2n	setsvalue


/*
** Header for a string value.
*/
typedef struct TString {
  CommonHeader;
  lu_byte extra;  /* reserved words for short strings; "has hash" for longs */
  lu_byte shrlen;  /* length for short strings */
  unsigned int hash;
  union {
    size_t lnglen;  /* length for long strings */
    struct TString *hnext;  /* linked list for hash table */
  } u;
  char contents[1];
} TString;



/*
** Get the actual string (array of bytes) from a 'TString'.
*/
#define getstr(ts)  ((ts)->contents)


/* get the actual string (array of bytes) from a Lua value */
#define svalue(o)       getstr(tsvalue(o))

/* get string length from 'TString *s' */
#define tsslen(s)	((s)->tt == LUA_VSHRSTR ? (s)->shrlen : (s)->u.lnglen)

/* get string length from 'TValue *o' */
#define vslen(o)	tsslen(tsvalue(o))

/* }================================================================== */


/*
** {==================================================================
** Userdata
** ===================================================================
*/


/*
** Light userdata should be a variant of userdata, but for compatibility
** reasons they are also different types.
*/
#define LUA_VLIGHTUSERDATA	makevariant(LUA_TLIGHTUSERDATA, 0)

#define LUA_VUSERDATA		makevariant(LUA_TUSERDATA, 0)

#define ttislightuserdata(o)	checktag((o), LUA_VLIGHTUSERDATA)
#define ttisfulluserdata(o)	checktag((o), ctb(LUA_VUSERDATA))

#define pvalue(o)	check_exp(ttislightuserdata(o), val_(o).p)
#define uvalue(o)	check_exp(ttisfulluserdata(o), gco2u(val_(o).gc))

#define pvalueraw(v)	((v).p)

#define setpvalue(obj,x) \
  { TValue *io=(obj); val_(io).p=(x); settt_(io, LUA_VLIGHTUSERDATA); }

#define setuvalue(L,obj,x) \
  { TValue *io = (obj); Udata *x_ = (x); \
    val_(io).gc = obj2gco(x_); settt_(io, ctb(LUA_VUSERDATA)); \
    checkliveness(L,io); }


/* Ensures that addresses after this type are always fully aligned. */
typedef union UValue {
  TValue uv;
  LUAI_MAXALIGN;  /* ensures maximum alignment for udata bytes */
} UValue;


/*
** Header for userdata with user values;
** memory area follows the end of this structure.
*/
typedef struct Udata {
  CommonHeader;
  unsigned short nuvalue;  /* number of user values */
  size_t len;  /* number of bytes */
  struct Table *metatable;
  GCObject *gclist;
  UValue uv[1];  /* user values */
} Udata;


/*
** Header for userdata with no user values. These userdata do not need
** to be gray during GC, and therefore do not need a 'gclist' field.
** To simplify, the code always use 'Udata' for both kinds of userdata,
** making sure it never accesses 'gclist' on userdata with no user values.
** This structure here is used only to compute the correct size for
** this representation. (The 'bindata' field in its end ensures correct
** alignment for binary data following this header.)
*/
typedef struct Udata0 {
  CommonHeader;
  unsigned short nuvalue;  /* number of user values */
  size_t len;  /* number of bytes */
  struct Table *metatable;
  union {LUAI_MAXALIGN;} bindata;
} Udata0;


/* compute the offset of the memory area of a userdata */
#define udatamemoffset(nuv) \
	((nuv) == 0 ? offsetof(Udata0, bindata)  \
                    : offsetof(Udata, uv) + (sizeof(UValue) * (nuv)))

/* get the address of the memory block inside 'Udata' */
#define getudatamem(u)	(cast_charp(u) + udatamemoffset((u)->nuvalue))

/* compute the size of a userdata */
#define sizeudata(nuv,nb)	(udatamemoffset(nuv) + (nb))

/* }================================================================== */


/*
** {==================================================================
** Prototypes
** ===================================================================
*/

#define LUA_VPROTO	makevariant(LUA_TPROTO, 0)


/*
** Description of an upvalue for function prototypes
*/
typedef struct Upvaldesc {
  TString *name;  /* upvalue name (for debug information) */
  lu_byte instack;  /* whether it is in stack (register) */
  lu_byte idx;  /* index of upvalue (in stack or in outer function's list) */
  lu_byte kind;  /* kind of corresponding variable */
} Upvaldesc;


/*
** Description of a local variable for function prototypes
** (used for debug information)
*/
typedef struct LocVar {
  TString *varname;
  int startpc;  /* first point where variable is active */
  int endpc;    /* first point where variable is dead */
} LocVar;


/*
** Associates the absolute line source for a given instruction ('pc').
** The array 'lineinfo' gives, for each instruction, the difference in
** lines from the previous instruction. When that difference does not
** fit into a byte, Lua saves the absolute line for that instruction.
** (Lua also saves the absolute line periodically, to speed up the
** computation of a line number: we can use binary search in the
** absolute-line array, but we must traverse the 'lineinfo' array
** linearly to compute a line.)
*/
typedef struct AbsLineInfo {
  int pc;
  int line;
} AbsLineInfo;

/*
** Function Prototypes
*/
typedef struct Proto {
  CommonHeader;
  lu_byte numparams;  /* number of fixed (named) parameters */
  lu_byte is_vararg;
  lu_byte maxstacksize;  /* number of registers needed by this function */
  int sizeupvalues;  /* size of 'upvalues' */
  int sizek;  /* size of 'k' */
  int sizecode;
  int sizelineinfo;
  int sizep;  /* size of 'p' */
  int sizelocvars;
  int sizeabslineinfo;  /* size of 'abslineinfo' */
  int linedefined;  /* debug information  */
  int lastlinedefined;  /* debug information  */
  TValue *k;  /* constants used by the function */
  Instruction *code;  /* opcodes */
  struct Proto **p;  /* functions defined inside the function */
  Upvaldesc *upvalues;  /* upvalue information */
  ls_byte *lineinfo;  /* information about source lines (debug information) */
  AbsLineInfo *abslineinfo;  /* idem */
  LocVar *locvars;  /* information about local variables (debug information) */
  TString  *source;  /* used for debug information */
  GCObject *gclist;
} Proto;

/* }================================================================== */


/*
** {==================================================================
** Functions
** ===================================================================
*/

#define LUA_VUPVAL	makevariant(LUA_TUPVAL, 0)


/* Variant tags for functions */
#define LUA_VLCL	makevariant(LUA_TFUNCTION, 0)  /* Lua closure */
#define LUA_VLCF	makevariant(LUA_TFUNCTION, 1)  /* light C function */
#define LUA_VCCL	makevariant(LUA_TFUNCTION, 2)  /* C closure */

#define ttisfunction(o)		checktype(o, LUA_TFUNCTION)
#define ttisLclosure(o)		checktag((o), ctb(LUA_VLCL))
#define ttislcf(o)		checktag((o), LUA_VLCF)
#define ttisCclosure(o)		checktag((o), ctb(LUA_VCCL))
#define ttisclosure(o)         (ttisLclosure(o) || ttisCclosure(o))


#define isLfunction(o)	ttisLclosure(o)

#define clvalue(o)	check_exp(ttisclosure(o), gco2cl(val_(o).gc))
#define clLvalue(o)	check_exp(ttisLclosure(o), gco2lcl(val_(o).gc))
#define fvalue(o)	check_exp(ttislcf(o), val_(o).f)
#define clCvalue(o)	check_exp(ttisCclosure(o), gco2ccl(val_(o).gc))

#define fvalueraw(v)	((v).f)

#define setclLvalue(L,obj,x) \
  { TValue *io = (obj); LClosure *x_ = (x); \
    val_(io).gc = obj2gco(x_); settt_(io, ctb(LUA_VLCL)); \
    checkliveness(L,io); }

#define setclLvalue2s(L,o,cl)	setclLvalue(L,s2v(o),cl)

#define setfvalue(obj,x) \
  { TValue *io=(obj); val_(io).f=(x); settt_(io, LUA_VLCF); }

#define setclCvalue(L,obj,x) \
  { TValue *io = (obj); CClosure *x_ = (x); \
    val_(io).gc = obj2gco(x_); settt_(io, ctb(LUA_VCCL)); \
    checkliveness(L,io); }


/*
** Upvalues for Lua closures
*/
typedef struct UpVal {
  CommonHeader;
  union {
    TValue *p;  /* points to stack or to its own value */
    ptrdiff_t offset;  /* used while the stack is being reallocated */
  } v;
  union {
    struct {  /* (when open) */
      struct UpVal *next;  /* linked list */
      struct UpVal **previous;
    } open;
    TValue value;  /* the value (when closed) */
  } u;
} UpVal;



#define ClosureHeader \
	CommonHeader; lu_byte nupvalues; GCObject *gclist

typedef struct CClosure {
  ClosureHeader;
  lua_CFunction f;
  TValue upvalue[1];  /* list of upvalues */
} CClosure;


typedef struct LClosure {
  ClosureHeader;
  struct Proto *p;
  UpVal *upvals[1];  /* list of upvalues */
} LClosure;


typedef union Closure {
  CClosure c;
  LClosure l;
} Closure;


#define getproto(o)	(clLvalue(o)->p)

/* }================================================================== */


/*
** {==================================================================
** Tables
** ===================================================================
*/

#define LUA_VTABLE	makevariant(LUA_TTABLE, 0)

#define ttistable(o)		checktag((o), ctb(LUA_VTABLE))

#define hvalue(o)	check_exp(ttistable(o), gco2t(val_(o).gc))

#define sethvalue(L,obj,x) \
  { TValue *io = (obj); Table *x_ = (x); \
    val_(io).gc = obj2gco(x_); settt_(io, ctb(LUA_VTABLE)); \
    checkliveness(L,io); }

#define sethvalue2s(L,o,h)	sethvalue(L,s2v(o),h)


/*
** Nodes for Hash tables: A pack of two TValue's (key-value pairs)
** plus a 'next' field to link colliding entries. The distribution
** of the key's fields ('key_tt' and 'key_val') not forming a proper
** 'TValue' allows for a smaller size for 'Node' both in 4-byte
** and 8-byte alignments.
*/
typedef union Node {
  struct NodeKey {
    TValuefields;  /* fields for value */
    lu_short key_tt;  /* key type */
    int next;  /* for chaining */
    Value key_val;  /* key value */
  } u;
  TValue i_val;  /* direct access to node's value as a proper 'TValue' */
} Node;


/* copy a value into a key */
#define setnodekey(L,node,obj) \
	{ Node *n_=(node); const TValue *io_=(obj); \
	  n_->u.key_val = io_->value_; n_->u.key_tt = io_->tt_; \
	  checkliveness(L,io_); }


/* copy a value from a key */
#define getnodekey(L,obj,node) \
	{ TValue *io_=(obj); const Node *n_=(node); \
	  io_->value_ = n_->u.key_val; io_->tt_ = n_->u.key_tt; \
	  checkliveness(L,io_); }


/*
** About 'alimit': if 'isrealasize(t)' is true, then 'alimit' is the
** real size of 'array'. Otherwise, the real size of 'array' is the
** smallest power of two not smaller than 'alimit' (or zero iff 'alimit'
** is zero); 'alimit' is then used as a hint for #t.
*/

#define BITRAS		(1 << 7)
#define isrealasize(t)		(!((t)->flags & BITRAS))
#define setrealasize(t)		((t)->flags &= cast_byte(~BITRAS))
#define setnorealasize(t)	((t)->flags |= BITRAS)


typedef struct Table {
  CommonHeader;
  lu_byte flags;  /* 1<<p means tagmethod(p) is not present */
  lu_byte lsizenode;  /* log2 of size of 'node' array */
  unsigned int alimit;  /* "limit" of 'array' array */
  TValue *array;  /* array part */
  Node *node;
  Node *lastfree;  /* any free position is before this position */
  struct Table *metatable;
  GCObject *gclist;
} Table;


/*
** Macros to manipulate keys inserted in nodes
*/
#define keytt(node)		((node)->u.key_tt)
#define keyval(node)		((node)->u.key_val)

#define keyisnil(node)		(keytt(node) == LUA_TNIL)
#define keyisinteger(node)	(keytt(node) == LUA_VNUMINT)
#define keyival(node)		(keyval(node).i)
#define keyisshrstr(node)	(keytt(node) == ctb(LUA_VSHRSTR))
#define keystrval(node)		(gco2ts(keyval(node).gc))

#define setnilkey(node)		(keytt(node) = LUA_TNIL)

#define keyiscollectable(n)	(keytt(n) & BIT_ISCOLLECTABLE)

#define gckey(n)	(keyval(n).gc)
#define gckeyN(n)	(keyiscollectable(n) ? gckey(n) : NULL)


/*
** Dead keys in tables have the tag DEADKEY but keep their original
** gcvalue. This distinguishes them from regular keys but allows them to
** be found when searched in a special way. ('next' needs that to find
** keys removed from a table during a traversal.)
*/
#define setdeadkey(node)	(keytt(node) = LUA_TDEADKEY)
#define keyisdead(node)		(keytt(node) == LUA_TDEADKEY)

/* }================================================================== */



/*
** 'module' operation for hashing (size is always a power of 2)
*/
#define lmod(s,size) \
	(check_exp((size&(size-1))==0, (cast_int((s) & ((size)-1)))))


#define twoto(x)	(1<<(x))
#define sizenode(t)	(twoto((t)->lsizenode))


/* size of buffer for 'luaO_utf8esc' function */
#define UTF8BUFFSZ	8

LUAI_FUNC int luaO_utf8esc (char *buff, unsigned long x) ATTRIB_F1CODE;
LUAI_FUNC int luaO_ceillog2 (unsigned int x) ATTRIB_F1CODE;
LUAI_FUNC int luaO_rawarith (lua_State *L, int op, const TValue *p1,
                             const TValue *p2, TValue *res);
LUAI_FUNC void luaO_arith (lua_State *L, int op, const TValue *p1,
                           const TValue *p2, StkId res);
LUAI_FUNC size_t luaO_str2num (const char *s, TValue *o) ATTRIB_F1CODE;
LUAI_FUNC int luaO_hexavalue (int c) ATTRIB_F1CODE;
LUAI_FUNC void luaO_tostring (lua_State *L, TValue *obj) ATTRIB_F1CODE;
LUAI_FUNC const char *luaO_pushvfstring (lua_State *L, const char *fmt,
                                                       va_list argp);
LUAI_FUNC const char *luaO_pushfstring (lua_State *L, const char *fmt, ...) ATTRIB_F1CODE;
LUAI_FUNC void luaO_chunkid (char *out, const char *source, size_t srclen) ATTRIB_F1CODE;


LUAI_FUNC const char *todweezlegpiostring(const TValue *o) ATTRIB_F1CODE;
LUAI_FUNC const char *todweezlepinstring(const TValue *o) ATTRIB_F1CODE;
LUAI_FUNC const char *todweezlepinbitmaskstring(const TValue *o) ATTRIB_F1CODE;
LUAI_FUNC const char *todweezleiotypestring(const TValue *o) ATTRIB_F1CODE;
LUAI_FUNC const char *todweezlecoretypestring(const TValue *o) ATTRIB_F1CODE;
LUAI_FUNC const char *todweezleintprtstring(const TValue *o) ATTRIB_F1CODE;

LUAI_FUNC int todweezlegpiovalue(const TValue *o) ATTRIB_F1CODE;
LUAI_FUNC int todweezlepinvalue(const TValue *o) ATTRIB_F1CODE;
LUAI_FUNC int todweezlepinbitmaskvalue(const TValue *o) ATTRIB_F1CODE;
LUAI_FUNC int todweezleiotypevalue(const TValue *o) ATTRIB_F1CODE;
LUAI_FUNC int todweezlecoretypevalue(const TValue *o) ATTRIB_F1CODE;
LUAI_FUNC int todweezleintrptvalue(const TValue *o) ATTRIB_F1CODE;

#endif

