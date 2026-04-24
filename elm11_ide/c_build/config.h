#ifndef CONFIG_H
#define CONFIG_H

// TODO: cleanup

#define ATTRIB_RUNTIMECODE __attribute__ ((section (".runtimecode")))

#define ATTRIB_FASTESTCODE __attribute__ ((section (".fastestcode")))
#define ATTRIB_FASTERCODE __attribute__ ((section (".fastercode")))
#define ATTRIB_FASTCODE __attribute__ ((section (".fastcode")))

#define ATTRIB_RUNTIMECODE_BUILDSWITCH __attribute__ ((section (".runtimecode")))
#define ATTRIB_FASTCODE_BUILDSWITCH __attribute__ ((section (".fastcode")))

#define ATTRIB_RUNTIMECODE_FLASHIO __attribute__ ((section (".runtimecode"))) __attribute__ ((noinline))

#define LUA_STATE_IN_RAM

#endif