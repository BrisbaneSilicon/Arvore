#define LUA_LIB

#include "lprefix.h"

#include <limits.h>
#include <stddef.h>
#include <string.h>

#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"


// Function prototypes

static int luaU_pin1_4xtoggle (lua_State *L);
static int luaU_lfsr32_next (lua_State *L);
static int luaU_even (lua_State *L);


// Implementation


/* ------------------ Users Lua API ----------------------  */


    // NOTE: User to add any custom API
    // functions here.



static const luaL_Reg user_funcs_dynamic[] = {
    // NOTE: ensure you add any new custom API
    // functions to this array in order to ensure
    // they can be imported from the Lua Interpreter.

    // NOTE: the below function Names, Pointers
    // are from the examples below.

    {"pin1_4xtoggle", luaU_pin1_4xtoggle},
    {"lfsr32_next", luaU_lfsr32_next},
    {"even", luaU_even},

    {NULL, NULL}
};


/* --------------- Example Users Lua API -------------------  */

/*
** Toggle PIN1 four times as quickly as possible.
**
** NOTE: assumes PIN1 is already configured as
** a GPIO_OUT, throws an error otherwise.
**
** Returns nothing.
*/
static int luaU_pin1_4xtoggle (lua_State *L) {
    const int c_pin1 = 1;

    e_status ret;
    int i;

    int n = lua_gettop(L);
    if (n != 0) {
        // NOTE: verify no arguments have
        // been passed to the function.

        luaL_error(L, "unexpected argument");
    }

    for (i = 0; i < 4; ++i) {
        ret = set_gpio(c_pin1, e_level_toggle);
            // NOTE: function 'set_gpio' is defined
            // in 'io.h'

        if(ret != e_success) {
            luaL_error(L, "failed to toggle PIN1. Reason: %s. "
                            "Iteration: %d", status_to_str(ret), i);
        }
    }

    return 0;
        // NOTE: no results were pushed onto the
        // the Lua stack.
}

/*
** Calculate and return 32-bit LFSR
** of the input integer argument.
**
** Returns the 32-bit LFSR result.
*/
static int luaU_lfsr32_next (lua_State *L) {
    lua_Integer lfsr_val;
    lua_Integer lfsr_result;
    char c;

    int n = lua_gettop(L);
    if (n != 1) {
        // NOTE: verify one argument has
        // been passed to the function.

        luaL_error(L, "unexpected argument");
    }

    lfsr_val = luaL_checkinteger(L, 1);
        // NOTE: check first argument is an integer

    c = (char)(lfsr_val >> 23) ^ (char)(lfsr_val >> 21);
    c ^= (char)(lfsr_val >>  7) ^  (char)lfsr_val;
    c &= 1u;

    lfsr_result = (lfsr_val << 1) | c;

    lua_pushinteger(L, lfsr_result);
        // NOTE: push 32-bit LFSR result onto
        // the Lua stack.

    return 1;
        // NOTE: one result was pushed onto the
        // the Lua stack.
}


/*
** Calculate if the first arg is even. Takes
** two possible responses as second and third
** arguments.
**
** Returns:
**  - True / False if the first arg is even
**  - Either the first response (if even) or
**      second (if odd).
*/
static int luaU_even (lua_State *L) {
    const char *pass_str;
    const char *fail_str;
    int val;

    int n = lua_gettop(L);
    if (n != 3) {
        luaL_error(L, "unexpected argument");
    }

    val = luaL_checkinteger(L, 1);
    pass_str = luaL_checkstring(L, 2);
    fail_str = luaL_checkstring(L, 3);

    if(val & 1) {
        // NOTE: 'val' is odd
        lua_pushboolean(L, 0);
        lua_pushstring(L, fail_str);

    } else {
        // NOTE: 'val' is even
        lua_pushboolean(L, 1);
        lua_pushstring(L, pass_str);
    }

    return 2;
}


/* ------------------ Boilerplate Library Code ----------------------  */

    // NOTE: you shouldn't need to touch
    // any of this...


static const luaL_Reg userlib_default[] = {
    {NULL, NULL}
};

/*
** Open user library
*/
LUAMOD_API int luaopen_user (lua_State *L) {
    luaL_newlib(L, userlib_default);
    return 1;
}

LUAMOD_API int luaimportfunc_user (lua_State *L, const char *fname) {
    uint32_t i;

    i = 0;
    while(1) {
        if (!user_funcs_dynamic[i].name) {
            return 1;
        }

        if (strcmp(fname, user_funcs_dynamic[i].name) == 0) {
            lua_getglobal(L, LUA_USERLIBNAME);
            luaL_setfunc(L, &user_funcs_dynamic[i], 0);

            break;
        }

        i++;
    }

    return 0;
}
