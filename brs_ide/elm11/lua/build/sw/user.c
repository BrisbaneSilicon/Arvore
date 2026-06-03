#define LUA_LIB

#include "lprefix.h"

#include <limits.h>
#include <stddef.h>
#include <string.h>

#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"


// Implementation


/* ------------------ Users Lua API ----------------------  */

    // NOTE: User to add any custom API
    // functions here.


    // NOTE: Ensure that all API funcitons are
    // included in the 'User API Registry' below,
    // in order for them to be callable from the
    // Lua appliction layer.


/* ------------------- Example Lua API --------------------  */

/*
** Toggle provided PIN as quickly as possible.
**
** NOTE: assumes the provided PIN is already
** configured asa GPIO_OUT, throws an error
** otherwise.
**
** Returns nothing.
*/
static int luaU_quick_toggle (lua_State *L) {
    e_status ret;
    int i;

    int pin;

    int n = lua_gettop(L);
    if (n != 1) {
        // NOTE: verify one argument has
        // been passed to the function.

        luaL_error(L, "unexpected argument");
    }

    pin = luaL_checkinteger(L, 1);
        // NOTE: check first argument is an integer

    for (i = 0; i < 100000; ++i) {
        ret = set_gpio(pin, e_level_toggle);
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
    c ^= (char)(lfsr_val >>  7) ^ (char)lfsr_val;
    c &= 1u;

    lfsr_result = (lfsr_val << 1) | c;

    lua_pushinteger(L, lfsr_result);
        // NOTE: push 32-bit LFSR result onto
        // the Lua stack.
    lua_pushinteger(L, lfsr_val);
        // NOTE: push argument (i.e. previous LFSR
        // result) onto the Lua stack.

    return 2;
        // NOTE: two results were pushed onto the
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
static int luaU_is_even (lua_State *L) {
    int val;

    int n = lua_gettop(L);
    if (n != 1) {
        luaL_error(L, "unexpected argument");
    }

    val = luaL_checkinteger(L, 1);
    if(val & 1) {
        lua_pushboolean(L, 0);
    } else {
        lua_pushboolean(L, 1);
    }

    return 1;
}

/*
** Fetch the next 32-bit LFSR value from
** hardware.
**
** Returns the next 32-bit hardware LFSR
** value.
*/
static int luaU_hw_lfsr32 (lua_State *L) {
    int n = lua_gettop(L);
    if (n != 0) {
        // NOTE: verify one argument has
        // been passed to the function.

        luaL_error(L, "unexpected argument");
    }

    lua_pushinteger(L, hw_read(1));
        // NOTE: push 32-bit LFSR result (read from
        // address one) onto the Lua stack.

    return 1;
}


/* ------------------ User API Registry ----------------------------  */

static const luaL_Reg user_api_registry[] = {
    // NOTE: ensure you add any new custom API
    // functions to this array in order to ensure
    // they can be imported from the Lua Interpreter.

    // NOTE: the { "Function Name", Function Pointer } entries
    // below are the 'Example Lua API' functions that are
    // defined previously.

    {"quick_toggle", luaU_quick_toggle},
    {"lfsr32_next", luaU_lfsr32_next},
    {"is_even", luaU_is_even},

    {"hw_lfsr32", luaU_hw_lfsr32},

    {NULL, NULL}
};


/* ------------------ Boilerplate Library Code ----------------------  */

// NOTE: users shouldn't need to
// touch any of this...


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
        if (!user_api_registry[i].name) {
            return 1;
        }

        if (strcmp(fname, user_api_registry[i].name) == 0) {
            lua_getglobal(L, LUA_USERLIBNAME);
            luaL_setfunc(L, &user_api_registry[i], 0);

            break;
        }

        i++;
    }

    return 0;
}
