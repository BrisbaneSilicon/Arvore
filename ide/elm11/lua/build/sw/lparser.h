/*
** $Id: lparser.h $
** Lua Parser
** See Copyright Notice in lua.h
*/

#ifndef lparser_h
#define lparser_h

#include "llimits.h"
#include "lobject.h"
#include "lzio.h"


/*
** Expression and variable descriptor.
** Code generation for variables and expressions can be delayed to allow
** optimizations; An 'expdesc' structure describes a potentially-delayed
** variable/expression. It has a description of its "main" value plus a
** list of conditional jumps that can also produce its value (generated
** by short-circuit operators 'and'/'or').
*/

/* kinds of variables/expressions */
typedef enum {
  VVOID,  /* when 'expdesc' describes the last expression of a list,
             this kind means an empty list (so, no expression) */
  VNIL,  /* constant nil */
  VTRUE,  /* constant true */
  VFALSE,  /* constant false */
  VLOW, /* constant low */
  VHIGH, /* constant high */
  VTOGGLE, /* constant toggle */
  VPIN1, /* PIN */
  VPIN2,
  VPIN3,
  VPIN4,
  VPIN5,
  VPIN6,
  VPIN7,
  VPIN8,
  VPIN9,
  VPIN10,
  VPIN11,
  VPIN12,
  VPIN13,
  VPIN14,
  VPIN15,
  VPIN16,
  VPIN17,
  VPIN18,
  VPIN19,
  VPIN20,
  VPIN21,
  VPIN22,
  VPIN23,
  VPIN24,
  VPIN25,
  VPIN26,
  VPIN27,
  VPIN28,
  VPIN29,
  VPIN30,
  VPIN31,
  VPIN32,
  VPIN1_BITMASK, /* PIN Bitmasks */
  VPIN2_BITMASK,
  VPIN3_BITMASK,
  VPIN4_BITMASK,
  VPIN5_BITMASK,
  VPIN6_BITMASK,
  VPIN7_BITMASK,
  VPIN8_BITMASK,
  VPIN9_BITMASK,
  VPIN10_BITMASK,
  VPIN11_BITMASK,
  VPIN12_BITMASK,
  VPIN13_BITMASK,
  VPIN14_BITMASK,
  VPIN15_BITMASK,
  VPIN16_BITMASK,
  VPIN17_BITMASK,
  VPIN18_BITMASK,
  VPIN19_BITMASK,
  VPIN20_BITMASK,
  VPIN21_BITMASK,
  VPIN22_BITMASK,
  VPIN23_BITMASK,
  VPIN24_BITMASK,
  VPIN25_BITMASK,
  VPIN26_BITMASK,
  VPIN27_BITMASK,
  VPIN28_BITMASK,
  VPIN29_BITMASK,
  VPIN30_BITMASK,
  VPIN31_BITMASK,
  VPIN32_BITMASK,
  VIO_TYPE_NONE, /* IO Types */
  VIO_TYPE_GPIO_OUT,
  VIO_TYPE_GPIO_IN,
  VIO_TYPE_PWM,
  VIO_TYPE_UART_OUT,
  VIO_TYPE_UART_IN,
  VIO_TYPE_SPI_OUT,
  VIO_TYPE_SPI_IN,
  VIO_TYPE_I2C,
  VIO_CTYPE_CORE1,
  VIO_CTYPE_CORE2,
  VIO_CTYPE_CORE3,
  VIO_CTYPE_CORE4,
  VIO_CTYPE_CORE5,
  VIO_CTYPE_CORE6,
  VIO_CTYPE_CORE7,
  VIO_CTYPE_CORE8,
  VGPIO_INTRPT_GND,
  VGPIO_INTRPT_VCC,
  VGPIO_INTRPT_RISING_EDGE,
  VGPIO_INTRPT_FALLING_EDGE,
  VUART_RX_INTRPT_DATA_AVAILABLE,
  VK,  /* constant in 'k'; info = index of constant in 'k' */
  VKFLT,  /* floating constant; nval = numerical float value */
  VKINT,  /* integer constant; ival = numerical integer value */
  VKSTR,  /* string constant; strval = TString address;
             (string is fixed by the lexer) */
  VNONRELOC,  /* expression has its value in a fixed register;
                 info = result register */
  VLOCAL,  /* local variable; var.ridx = register index;
              var.vidx = relative index in 'actvar.arr'  */
  VUPVAL,  /* upvalue variable; info = index of upvalue in 'upvalues' */
  VCONST,  /* compile-time <const> variable;
              info = absolute index in 'actvar.arr'  */
  VINDEXED,  /* indexed variable;
                ind.t = table register;
                ind.idx = key's R index */
  VINDEXUP,  /* indexed upvalue;
                ind.t = table upvalue;
                ind.idx = key's K index */
  VINDEXI, /* indexed variable with constant integer;
                ind.t = table register;
                ind.idx = key's value */
  VINDEXSTR, /* indexed variable with literal string;
                ind.t = table register;
                ind.idx = key's K index */
  VJMP,  /* expression is a test/comparison;
            info = pc of corresponding jump instruction */
  VRELOC,  /* expression can put result in any register;
              info = instruction pc */
  VCALL,  /* expression is a function call; info = instruction pc */
  VVARARG  /* vararg expression; info = instruction pc */
} expkind;


#define vkisvar(k)	(VLOCAL <= (k) && (k) <= VINDEXSTR)
#define vkisindexed(k)	(VINDEXED <= (k) && (k) <= VINDEXSTR)


typedef struct expdesc {
  expkind k;
  union {
    lua_Integer ival;    /* for VKINT */
    lua_Number nval;  /* for VKFLT */
    TString *strval;  /* for VKSTR */
    int info;  /* for generic use */
    struct {  /* for indexed variables */
      short idx;  /* index (R or "long" K) */
      lu_byte t;  /* table (register or upvalue) */
    } ind;
    struct {  /* for local variables */
      lu_byte ridx;  /* register holding the variable */
      unsigned short vidx;  /* compiler index (in 'actvar.arr')  */
    } var;
  } u;
  int t;  /* patch list of 'exit when true' */
  int f;  /* patch list of 'exit when false' */
} expdesc;


/* kinds of variables */
#define VDKREG		0   /* regular */
#define RDKCONST	1   /* constant */
#define RDKTOCLOSE	2   /* to-be-closed */
#define RDKCTC		3   /* compile-time constant */

/* description of an active local variable */
typedef union Vardesc {
  struct {
    TValuefields;  /* constant value (if it is a compile-time constant) */
    lu_byte kind;
    lu_byte ridx;  /* register holding the variable */
    short pidx;  /* index of the variable in the Proto's 'locvars' array */
    TString *name;  /* variable name */
  } vd;
  TValue k;  /* constant value (if any) */
} Vardesc;



/* description of pending goto statements and label statements */
typedef struct Labeldesc {
  TString *name;  /* label identifier */
  int pc;  /* position in code */
  int line;  /* line where it appeared */
  lu_byte nactvar;  /* number of active variables in that position */
  lu_byte close;  /* goto that escapes upvalues */
} Labeldesc;


/* list of labels or gotos */
typedef struct Labellist {
  Labeldesc *arr;  /* array */
  int n;  /* number of entries in use */
  int size;  /* array size */
} Labellist;


/* dynamic structures used by the parser */
typedef struct Dyndata {
  struct {  /* list of all active local variables */
    Vardesc *arr;
    int n;
    int size;
  } actvar;
  Labellist gt;  /* list of pending gotos */
  Labellist label;   /* list of active labels */
} Dyndata;


/* control of blocks */
struct BlockCnt;  /* defined in lparser.c */


/* state needed to generate code for a given function */
typedef struct FuncState {
  Proto *f;  /* current function header */
  struct FuncState *prev;  /* enclosing function */
  struct LexState *ls;  /* lexical state */
  struct BlockCnt *bl;  /* chain of current blocks */
  int pc;  /* next position to code (equivalent to 'ncode') */
  int lasttarget;   /* 'label' of last 'jump label' */
  int previousline;  /* last line that was saved in 'lineinfo' */
  int nk;  /* number of elements in 'k' */
  int np;  /* number of elements in 'p' */
  int nabslineinfo;  /* number of elements in 'abslineinfo' */
  int firstlocal;  /* index of first local var (in Dyndata array) */
  int firstlabel;  /* index of first label (in 'dyd->label->arr') */
  short ndebugvars;  /* number of elements in 'f->locvars' */
  lu_byte nactvar;  /* number of active local variables */
  lu_byte nups;  /* number of upvalues */
  lu_byte freereg;  /* first free register */
  lu_byte iwthabs;  /* instructions issued since last absolute line info */
  lu_byte needclose;  /* function needs to close upvalues when returning */
} FuncState;


LUAI_FUNC int luaY_nvarstack (FuncState *fs);
LUAI_FUNC LClosure *luaY_parser (lua_State *L, ZIO *z, Mbuffer *buff,
                                 Dyndata *dyd, const char *name, int firstchar);


#endif
