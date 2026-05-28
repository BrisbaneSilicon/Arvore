/*
** $Id: luserlib_c.c $
** User Library - Example
*/

#define luserlib_c
#define LUA_LIB

#include "lprefix.h"

#include <limits.h>
#include <stddef.h>
#include <string.h>

#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"

#include "stdlib.h"
#include "memory_gowin.h"


static int luaU_lfsr32_next (lua_State *L) {
    lua_Integer lfsr_val;
    char c;

    lfsr_val = luaL_checkinteger(L, 1);

    int n = lua_gettop(L);
    if (n != 1) {
        luaL_error(L, "unexpected argument");
    }

    c = (char)(lfsr_val >> 23) ^ (char)(lfsr_val >> 21);
    c ^= (char)(lfsr_val >>  7) ^  (char)lfsr_val;
    c &= 1u;

    lua_pushinteger(L, (lfsr_val << 1) | c);

    return 1;
}


/*
** NOTE: assumes PIN1 is already configured as
** a GPIO_OUT.
*/
static int luaU_pin1_4xtoggle (lua_State *L) {
    const int c_pin1 = 1;
    e_status ret;
    int i;

    int n = lua_gettop(L);
    if (n != 0) {
        luaL_error(L, "unexpected argument");
    }

    for (i = 0; i < 4; ++i) {
        ret = set_gpio(c_pin1, e_level_toggle);
        if(ret != e_success) {
            luaL_error(L, "failed to toggle PIN1. Reason: %s. Iteration: %d", status_to_str(ret), i);
        }
    }

    return 0;
}


static const luaL_Reg user_funcs_dynamic[] = {
    {"lfsr32_next", luaU_lfsr32_next},
    {"pin1_4xtoggle", luaU_pin1_4xtoggle},
    {NULL, NULL}
};


/* }====================================================== */


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
