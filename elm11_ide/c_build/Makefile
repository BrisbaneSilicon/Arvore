PROJ_NAME=flash
BENCH=no
MULDIV=no
COMPRESSED=no

TARGET_DEVICE ?= NONE
TARGET_DEVICE_SHORT ?= NONE
STACK_SIZE_BYTES ?= 8192

OUTPUT_ARTEFACTS_NAME=$(PROJ_NAME)

BUILDDIR = build
ARTEFACTDIR = artefacts
DIFF_FILE = .tmp.diff
TARGET_FILE = .target
INIT_DIRS := $(shell if [ ! -e $(BUILDDIR)/$(ARTEFACTDIR) ]; then mkdir -p $(BUILDDIR)/$(ARTEFACTDIR); fi)

GIT_SHORTREV := $(shell echo "$(TARGET_DEVICE)" > $(BUILDDIR)/$(ARTEFACTDIR)/$(TARGET_FILE))

GIT_SHORTREV := $(shell git rev-parse --short HEAD)
GIT_LOCAL_CHANGES := $(shell git diff HEAD . > $(BUILDDIR)/$(ARTEFACTDIR)/$(DIFF_FILE))
GIT_DIRTY := $(shell if [ -s "$(BUILDDIR)/$(ARTEFACTDIR)/$(DIFF_FILE)" ]; then echo "-dirty"; fi)
TIME_STR := $(shell date "+%F %T")
VSTRING := "$(GIT_SHORTREV)$(GIT_DIRTY)|$(TIME_STR)"
VMACRO := VERSION

SRCS =  $(wildcard */*.c) \
        $(wildcard *.c) \
        $(wildcard *.S)

DIRS=.
INC=$(addprefix -I, $(DIRS))


LDSCRIPT = ./linkers/$(TARGET_DEVICE)/linker_stack$(STACK_SIZE_KBYTES)kb.ld

RISCV_NAME ?= riscv-none-elf
RISCV_PATH ?= /opt/toolchains/risc-v/xpack-riscv-none-elf-gcc-13.2.0-2

PYTHON_NAME ?= python
VDUMPC_PATH ?= ../sw/vdump8to32.py
EELF_PATH ?= ../sw/eelf.py
MEM_SIZE_KB ?= 512
    # NOTE: Flash is actually 8MB, but we are using (well) less than
    # 0.5 MB... so just dump that, for the sake of brevity..

MABI=ilp32
MARCH := rv32i
ifeq ($(MULDIV),yes)
    MARCH := $(MARCH)m
endif
ifeq ($(COMPRESSED),yes)
    MARCH := $(MARCH)ac
endif

CFLAGS += -Wall -march=$(MARCH) -mabi=$(MABI) -ffunction-sections -fdata-sections -MD -fstrict-volatile-bitfields
ifeq ($(BENCH),yes)
    CFLAGS += -fno-inline  
endif

DEFFLAG := -D



CFLAGS += -O1
# NOTE: According to 'https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html'
# the below group of compiler flags are included in 'O1'...
# (but see O2-related comment below... so I am going to include them
# manually anyway...).
CFLAGS += -fauto-inc-dec
CFLAGS += -fbranch-count-reg
CFLAGS += -fcombine-stack-adjustments
CFLAGS += -fcompare-elim
CFLAGS += -fcprop-registers
CFLAGS += -fdce
CFLAGS += -fdefer-pop
CFLAGS += -fdse
CFLAGS += -fforward-propagate
CFLAGS += -fguess-branch-probability
CFLAGS += -fif-conversion
CFLAGS += -fif-conversion2
CFLAGS += -finline-functions-called-once
CFLAGS += -fipa-modref
CFLAGS += -fipa-profile
CFLAGS += -fipa-pure-const
CFLAGS += -fipa-reference
CFLAGS += -fipa-reference-addressable
CFLAGS += -fmerge-constants
CFLAGS += -fmove-loop-invariants
CFLAGS += -fmove-loop-stores
CFLAGS += -fomit-frame-pointer
CFLAGS += -freorder-blocks
CFLAGS += -fshrink-wrap
CFLAGS += -fshrink-wrap-separate
CFLAGS += -fsplit-wide-types
CFLAGS += -fssa-backprop
CFLAGS += -fssa-phiopt
CFLAGS += -ftree-bit-ccp
CFLAGS += -ftree-ccp
CFLAGS += -ftree-ch
CFLAGS += -ftree-coalesce-vars
CFLAGS += -ftree-copy-prop
CFLAGS += -ftree-dce
CFLAGS += -ftree-dominator-opts
CFLAGS += -ftree-dse
CFLAGS += -ftree-forwprop
CFLAGS += -ftree-fre
CFLAGS += -ftree-phiprop
CFLAGS += -ftree-pta
CFLAGS += -ftree-scev-cprop
CFLAGS += -ftree-sink
CFLAGS += -ftree-slsr
CFLAGS += -ftree-sra
CFLAGS += -ftree-ter
CFLAGS += -funit-at-a-time

# NOTE: According to 'https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html'
# the below group of compiler flags are included in 'O2'...
# (but O2 breaks for-loop initialisation to '0'... so something is off...).
CFLAGS += -falign-functions  -falign-jumps
CFLAGS += -falign-labels  -falign-loops
CFLAGS += -fcaller-saves
CFLAGS += -fcode-hoisting
CFLAGS += -fcrossjumping
CFLAGS += -fcse-follow-jumps  -fcse-skip-blocks
CFLAGS += -fdelete-null-pointer-checks
CFLAGS += -fdevirtualize  -fdevirtualize-speculatively
CFLAGS += -fexpensive-optimizations
CFLAGS += -ffinite-loops
CFLAGS += -fgcse  -fgcse-lm
CFLAGS += -fhoist-adjacent-loads
CFLAGS += -finline-functions
CFLAGS += -finline-small-functions
CFLAGS += -findirect-inlining
CFLAGS += -fipa-bit-cp  -fipa-cp  -fipa-icf
CFLAGS += -fipa-ra  -fipa-sra  -fipa-vrp
CFLAGS += -fisolate-erroneous-paths-dereference
CFLAGS += -flra-remat
CFLAGS += -foptimize-sibling-calls
CFLAGS += -foptimize-strlen
CFLAGS += -fpartial-inlining
CFLAGS += -fpeephole2
CFLAGS += -freorder-blocks-algorithm=stc
CFLAGS += -freorder-blocks-and-partition  -freorder-functions
CFLAGS += -frerun-cse-after-loop
CFLAGS += -fschedule-insns  -fschedule-insns2
CFLAGS += -fsched-interblock  -fsched-spec
CFLAGS += -fstore-merging
CFLAGS += -fstrict-aliasing
CFLAGS += -fthread-jumps
CFLAGS += -ftree-builtin-call-dce
CFLAGS += -ftree-loop-vectorize
CFLAGS += -ftree-pre
CFLAGS += -ftree-slp-vectorize
CFLAGS += -ftree-switch-conversion  -ftree-tail-merge
CFLAGS += -ftree-vrp
CFLAGS += -fvect-cost-model=very-cheap

# NOTE: According to 'https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html'
# the below group of compiler flags are included in 'O3'...
# (but O3 breaks for-loop initialisation to '0'... so something is off...).
CFLAGS += -fgcse-after-reload
CFLAGS += -fipa-cp-clone
CFLAGS += -floop-interchange
CFLAGS += -floop-unroll-and-jam
CFLAGS += -fpeel-loops
CFLAGS += -fpredictive-commoning
CFLAGS += -fsplit-loops
CFLAGS += -fsplit-paths
CFLAGS += -ftree-loop-distribution
CFLAGS += -ftree-partial-pre
CFLAGS += -funswitch-loops
CFLAGS += -fvect-cost-model=dynamic
CFLAGS += -fversion-loops-for-strides
CFLAGS += -funroll-loops


LDFLAGS += -march=$(MARCH)  -mabi=$(MABI)  -Wl,--gc-sections -nostdlib -lm -lgcc -mcmodel=medany -nostartfiles
LDFLAGS += -ffreestanding -Wl,-Bstatic,-T,$(LDSCRIPT),-Map,$(BUILDDIR)/$(OUTPUT_ARTEFACTS_NAME).map,--print-memory-usage
LDFLAGS += -lc_nano

RISCV_CLIB = $(RISCV_PATH)/$(RISCV_NAME)/lib/$(MARCH)/$(MABI)/
RISCV_OBJCOPY = $(RISCV_PATH)/bin/$(RISCV_NAME)-objcopy
RISCV_OBJDUMP = $(RISCV_PATH)/bin/$(RISCV_NAME)-objdump
RISCV_CC = $(RISCV_PATH)/bin/$(RISCV_NAME)-gcc

OBJS := $(SRCS)
OBJS := $(OBJS:.c=.o)
OBJS := $(OBJS:.cpp=.o)
OBJS := $(OBJS:.S=.o)
OBJS := $(addprefix $(BUILDDIR)/,$(OBJS))

SUBOBJ := $(addprefix $(BUILDDIR)/,$(SUBDIRS))
SUBOBJ := $(addsuffix /*.o,$(SUBOBJ))

export RISCV_CC CFLAGS LDFLAGS BUILDDIR

all: $(SUBDIRS) $(BUILDDIR)/$(OUTPUT_ARTEFACTS_NAME).elf $(BUILDDIR)/$(OUTPUT_ARTEFACTS_NAME).hex $(BUILDDIR)/$(OUTPUT_ARTEFACTS_NAME).mcs $(BUILDDIR)/$(OUTPUT_ARTEFACTS_NAME).asm $(BUILDDIR)/$(OUTPUT_ARTEFACTS_NAME).v $(BUILDDIR)/$(OUTPUT_ARTEFACTS_NAME).mif $(BUILDDIR)/$(OUTPUT_ARTEFACTS_NAME).gen

$(SUBDIRS): ECHOSUBDIRS
    make -C $@

ECHOSUBDIRS:
    @echo $(SUBDIRS)

$(BUILDDIR)/%.elf: $(OBJS) | $(BUILDDIR)
    $(RISCV_CC) $(CFLAGS) -o $@ $^ $(SUBOBJ) $(LDFLAGS) $(LIBS)

%.hex: %.elf
    $(RISCV_OBJCOPY) -O ihex $^ $@

%.bin: %.elf
    $(RISCV_OBJCOPY) -O binary $^ $@
    
%.v: %.elf
    $(RISCV_OBJCOPY) -O verilog $^ $@

%.mif: %.v
    $(PYTHON_NAME) $(VDUMPC_PATH) $^ $@ mif $(MEM_BASEADDR) $(MEM_SIZE_KB)

%.asm: %.elf
    $(RISCV_OBJDUMP) -S -d $^ > $@

%.mcs: %.hex
    cp $^ $@

%.eelf: %.elf
    $(PYTHON_NAME) $(EELF_PATH) $^ $@ $(MEM_BASEADDR)

$(BUILDDIR)/%.o: %.c
    mkdir -p $(dir $@)
    $(RISCV_CC) $(DEFFLAG)$(VMACRO)=$(VSTRING) $(DEFFLAG)STACK_SIZE_$(STACK_SIZE_BYTES) -c $(CFLAGS)  $(INC) -o $@ $^

$(BUILDDIR)/%.o: %.S
    mkdir -p $(dir $@)
    $(RISCV_CC) -c $(CFLAGS) -o $@ $^ -D__ASSEMBLY__=1

$(BUILDDIR):
    mkdir -p $@

clean:
    rm -rf $(BUILDDIR)

.SECONDARY: $(OBJS)


            
