/*
** $Id: lualib.h $
** Lua standard libraries
** See Copyright Notice in lua.h
*/


#ifndef lualib_h
#define lualib_h

#include "lua.h"


/* version suffix for environment variable names */
#define LUA_VERSUFFIX          "_" LUA_VERSION_MAJOR "_" LUA_VERSION_MINOR

#define LUA_BASLIBNAME  "base"
LUAMOD_API int (luaopen_base) (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;

#define LUA_COLIBNAME	"coroutine"
LUAMOD_API int (luaopen_coroutine) (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;

#define LUA_TABLIBNAME	"table"
LUAMOD_API int (luaopen_table) (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;
LUAMOD_API int (luaimportfunc_table) (lua_State *L, const char *fname) ATTRIB_F1CODE_BUILDSWITCH;

#define LUA_IOLIBNAME	"io"
LUAMOD_API int (luaopen_io) (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;

#define LUA_OSLIBNAME	"os"
LUAMOD_API int (luaopen_os) (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;

#define LUA_STRLIBNAME	"string"
LUAMOD_API int (luaopen_string) (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;
LUAMOD_API int (luaimportfunc_string) (lua_State *L, const char *fname) ATTRIB_F1CODE_BUILDSWITCH;

#define LUA_UTF8LIBNAME	"utf8"
LUAMOD_API int (luaopen_utf8) (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;

#define LUA_MATHLIBNAME	"math"
LUAMOD_API int (luaopen_math) (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;
LUAMOD_API int (luaimportfunc_math) (lua_State *L, const char *fname) ATTRIB_F1CODE_BUILDSWITCH;

#define LUA_USERLIBNAME "user"
LUAMOD_API int (luaopen_user) (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;
LUAMOD_API int (luaimportfunc_user) (lua_State *L, const char *fname) ATTRIB_F1CODE_BUILDSWITCH;

#define LUA_DBLIBNAME	"interrupt"
LUAMOD_API int (luaopen_debug) (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;
    // TODO: rename whole module to 'interrupt'

#define LUA_LOADLIBNAME	"package"
LUAMOD_API int (luaopen_package) (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;


/* open all previous libraries */
LUALIB_API void (luaL_openlibs) (lua_State *L) ATTRIB_F1CODE_BUILDSWITCH;


#endif
