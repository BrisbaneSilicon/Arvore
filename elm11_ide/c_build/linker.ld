/*
This is free and unencumbered software released into the public domain.

Anyone is free to copy, modify, publish, use, compile, sell, or
distribute this software, either in source code form or as a compiled
binary, for any purpose, commercial or non-commercial, and by any
means.
*/
OUTPUT_FORMAT("elf32-littleriscv", "elf32-littleriscv", "elf32-littleriscv")
OUTPUT_ARCH(riscv)
ENTRY(crtStart)

MEMORY
{
  FLASH     (rx)    : ORIGIN = 0x00000000, LENGTH = 8M /* entire flash, 8 MiB */
  BSS       (xrw)   : ORIGIN = 0x60000000, LENGTH = 1420
  STACK     (xrw)   : ORIGIN = 0x6000058C, LENGTH = 6700
  FASTHEAP  (xrw)   : ORIGIN = 0x80000000, LENGTH = 32k
  FASTCODE  (xrw)   : ORIGIN = 0x80008000, LENGTH = 256k
    /* REVISIT: values of origin and length
      should be passed as an arguments */
}

_heap_size = DEFINED(_heap_size)    ? _heap_size : 0;
_stack_size = DEFINED(_stack_size)  ? _stack_size : 6680;

SECTIONS {
    /* The program code and other data goes into FLASH */
  .vector : {
    . = ALIGN(4);
    *crt.o(.text);
  } > FLASH

  .text :
  {
    . = ALIGN(4);
    *(.text.boot)      /* .text.boot sections (code) */
    *(.text*)          /* .text* sections (code) */
    *(.eh_frame_hdr)
    *(.eh_frame)

    . = ALIGN(4);
    _etext = .;        /* define a global symbol at end of code */
    _sidata = _etext;  /* This is used by the startup in order to initialize the .data secion */
  } >FLASH

  .ctors :
  {
    . = ALIGN(4);
    _ctors_start = .;
    KEEP(*(.init_array*))
    KEEP (*(SORT(.ctors.*)))
    KEEP (*(.ctors))
    . = ALIGN(4);
    _ctors_end = .;
  } > FLASH

  /* This is the initialized data section
    The program executes knowing that the data is in the FASTCODE
    but the loader puts the initial values in the FLASH (inidata).
    It is one task of the startup to copy the initial values from FLASH to FASTCODE. */
  .data : AT ( _sidata )
  {
    . = ALIGN(4);
    _sdata = .;        /* create a global symbol at data start; used by startup code in order to initialise the .data section in FASTCODE */
    _datasection_start = .;
    *(.data)           /* .data sections */
    *(.data*)          /* .data* sections */
    *(.gnu.linkonce.d.*)
    . = ALIGN(8);
    PROVIDE( __global_pointer$ = . + 0x800 );
    _sdatasection_start = .;
    *(.sdata)           /* .sdata sections */
    *(.sdata*)          /* .sdata* sections */
    *(.gnu.linkonce.s.*)
    *(.rdata)
    _runtimecode_start = .;
    *(.runtimecode .runtimecode.*);
    _rodatasection_start = .;
    *(.rodata)         /* .rodata sections (constants, strings, etc.) */
    *(.rodata*)        /* .rodata* sections (constants, strings, etc.) */
    *(.srodata)        /* .rodata sections (constants, strings, etc.) */
    *(.srodata*)       /* .rodata* sections (constants, strings, etc.) */
    _ram_start = .;    /* create a global symbol at FASTCODE start for garbage collector */
    . = ALIGN(4);
    _fastcodesection_start = .;
    *(.fastestcode .fastestcode.*);
    *(.fastercode .fastercode.*);
    *(.fastcode .fastcode.*);
    *(.text)           /* .text sections (code) */
    . = ALIGN(4);
    _edata = .;        /* define a global symbol at data end; used by startup code in order to initialise the .data section in FASTCODE */
  } >FASTCODE

  /* this is to define the start of the heap, and make sure we have a minimum size */
  .heap :
  {
    . = ALIGN(8);
    PROVIDE ( _heap_start = .);    /* define a global symbol at heap start */
    . = . + _heap_size;
    . = ALIGN(8);
    PROVIDE ( _heap_end = .);
  } >FASTCODE


  /* Uninitialized data section */
  .bss :
  {
    . = ALIGN(4);
    _bss_start  = .;         /* define a global symbol at bss start; used by startup code */
    *(.bss)
    *(.bss*)
    *(.sbss)
    *(.sbss*)
    *(.gnu.linkonce.sb.*)
    *(.gnu.linkonce.b.*)
    *(COMMON)
    . = ALIGN(4);
    _bss_end = .;         /* define a global symbol at bss end; used by startup code */
  } >BSS

  .stack :
  {
    . = ALIGN(16);
    PROVIDE(_stack_end = .);
    . = _stack_size;
    . = ALIGN(16);
    PROVIDE(_stack_start = .);
  } >STACK

}
