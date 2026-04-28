#ifndef CONFIG_H
#define CONFIG_H

// ---------------------- Defines ----------------------

#define ATTRIB_RUNTIMECODE              __attribute__ ((section (".runtimecode")))

#define ATTRIB_F3CODE                   __attribute__ ((section (".f3code")))
#define ATTRIB_F2CODE                   __attribute__ ((section (".f2code")))
#define ATTRIB_F1CODE                   __attribute__ ((section (".f1code")))

#define ATTRIB_F1CODE_BUILDSWITCH       __attribute__ ((section (".f1code")))

#define ATTRIB_RUNTIMECODE_FLASHIO      __attribute__ ((section (".runtimecode"))) __attribute__ ((noinline))

#endif