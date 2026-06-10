#ifndef CONFIG_H
#define CONFIG_H

// TODO: cleanup


#ifndef TD_ARTY_S7
    #ifndef TD_GW1NR_9_C7I6_B
        #define ATTRIB_RUNTIMECODE __attribute__ ((section (".runtimecode")))

        #define ATTRIB_F3CODE __attribute__ ((section (".f3code")))
        #define ATTRIB_F2CODE __attribute__ ((section (".f2code")))
        #define ATTRIB_F1CODE __attribute__ ((section (".f1code")))
    #else
        #define ATTRIB_RUNTIMECODE

        #define ATTRIB_F3CODE
        #define ATTRIB_F2CODE
        #define ATTRIB_F1CODE
    #endif
#else
    #define ATTRIB_RUNTIMECODE

    #define ATTRIB_F3CODE
    #define ATTRIB_F2CODE
    #define ATTRIB_F1CODE
#endif

#if defined(TD_GW1NR_9_C6I5_S) || defined(TD_GW1NR_9_C7I6)
    #define ATTRIB_RUNTIMECODE_BUILDSWITCH __attribute__ ((section (".runtimecode")))

    #define ATTRIB_F1CODE_BUILDSWITCH __attribute__ ((section (".f1code")))
#else
    #define ATTRIB_F1CODE_BUILDSWITCH
#endif

#ifdef TD_GW1NR_9_C7I6_B
    #define DEBUG_DISABLE_HEAP

        // NOTE: No heap at all for this variant !
#endif

#ifdef DISABLE_FLASH
    #define DEBUG_DISABLE_FLASH

    #define ATTRIB_RUNTIMECODE_FLASHIO
#else
    #define ATTRIB_RUNTIMECODE_FLASHIO __attribute__ ((section (".runtimecode"))) __attribute__ ((noinline))
#endif

// NOTE: VPRINT == Verbose Print

// #define DEBUG
// #define DEBUG_VPRINT_LVM
// #define DEBUG_VPRINT_LVM_OP_MOVE
// #define DEBUG_VPRINT_LVM_GETTABUP
// #define DEBUG_VPRINT_LVM_DISPATCH
// #define DEBUG_VPRINT_LVM_LTABLE
// #define DEBUG_VPRINT_LVM_LDO
// #define DEBUG_VPRINT_LVM_STATE
// #define DEBUG_VPRINT_EN_GENERAL
// #define DEBUG_VPRINT_EN_FAST_HEAP
// #define DEBUG_VPRINT_EN_HEAP
// #define DEBUG_VPRINT_CPU_ACCESS
// #define DEBUG_INTERRUPTS

// #define BACKGROUND_COLOR_CHANGE_EN

// #define DEBUG_DISABLE_STACK
// #define DEBUG_DISABLE_HEAP
    // WARNING: double check - this might already be
    // defined above !!!

// #define DEBUG_DISABLE_FLASH
    // WARNING: double check - this might already be
    // defined above !!!


// #define DISABLE_FAST_HEAP

// #define ENABLE_LUA_ASSERTS

#endif