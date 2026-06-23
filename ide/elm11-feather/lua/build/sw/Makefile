# ELM11 C-workspace Makefile.
#
# Layout (deployed by the IDE when a new C workspace is created; the
# generated `.build/` tree is dot-prefixed so it stays hidden in the IDE):
#   <workspace>/.build/make/      — main.c, this Makefile + linker.ld
#   <workspace>/.build/utilities/ — eelf.py, vdump8to32.py
#   <workspace>/.build/runtime/   — prebuilt *.o runtime objects to link against
#
# Run with `make -C .build/make` from the workspace root, or
# `cd .build/make && make`.

# ── Project / target configuration ────────────────────────────────────────
PROJ_NAME           := NONE
TARGET_DEVICE       ?= NONE
TARGET_DEVICE_SHORT ?= NONE
STACK_SIZE_BYTES    ?= 8192
MEM_SIZE_KB         ?= 512
MEM_BASEADDR        ?=

# ISA options
BENCH               ?= no
MULDIV              ?= no
COMPRESSED          ?= no

# ── Toolchain ─────────────────────────────────────────────────────────────
RISCV_NAME          ?= riscv-none-elf
RISCV_PATH          ?= NONE
# `RISCV_PATH` can contain spaces (e.g. /opt/My Toolchains/...). Make stores
# the value verbatim but hands recipes to the shell unquoted, which would
# then tokenise on spaces. Build an escaped copy for use in recipes.
_SPACE              := $(subst ,, )
RISCV_PATH_ESC      := $(subst $(_SPACE),\$(_SPACE),$(RISCV_PATH))
RISCV_CC            := $(RISCV_PATH_ESC)/bin/$(RISCV_NAME)-gcc
RISCV_OBJCOPY       := $(RISCV_PATH_ESC)/bin/$(RISCV_NAME)-objcopy
RISCV_OBJDUMP       := $(RISCV_PATH_ESC)/bin/$(RISCV_NAME)-objdump

PYTHON              ?= python3

# ── Layout (relative to this Makefile) ────────────────────────────────────
WORKSPACE           := ../..
BUILDDIR            := ../out
ARTEFACTDIR         := $(BUILDDIR)/artefacts
LDSCRIPT            := ./linker.ld
RUNTIME_DIR         := ../runtime
HEADER_DIR          := ../header
UTIL_DIR            := ../utilities
EELF_PATH           := $(UTIL_DIR)/eelf.py
VDUMP_PATH          := $(UTIL_DIR)/vdump8to32.py

# ── Sources ───────────────────────────────────────────────────────────────
# Recursive directory walker — returns every subdirectory beneath $1.
_all_dirs            = $(foreach d,$(wildcard $(1)/*/), \
                          $(d:%/=%) $(call _all_dirs,$(d:%/=%)))
# Workspace directories that contain user code (workspace root + every
# nested subdirectory) — the `.build/` tree of generated artefacts is
# excluded so its files don't end up double-compiled. ($(wildcard) skips
# dot-prefixed dirs, so the hidden `.build` is already invisible to the
# walker; the filter-out is belt-and-braces.)
USER_DIRS           := $(WORKSPACE) \
                       $(filter-out $(WORKSPACE)/.build $(WORKSPACE)/.build/%, \
                                    $(call _all_dirs,$(WORKSPACE)))

SRCS                := $(foreach d,$(USER_DIRS), \
                          $(wildcard $(d)/*.c) $(wildcard $(d)/*.S))
# Startup / bootstrap assembly files bundled with the Makefile itself
# (e.g. crt_flash.S).
STARTUP_SRCS        := $(wildcard *.S)
# C sources bundled alongside the Makefile (e.g. main.c, the entry point).
LOCAL_SRCS          := $(wildcard *.c)
RUNTIME_OBJS        := $(wildcard $(RUNTIME_DIR)/*.o)
OBJS                := $(patsubst $(WORKSPACE)/%.c,$(BUILDDIR)/%.o,$(filter %.c,$(SRCS))) \
                       $(patsubst $(WORKSPACE)/%.S,$(BUILDDIR)/%.o,$(filter %.S,$(SRCS))) \
                       $(patsubst %.c,$(BUILDDIR)/local/%.o,$(LOCAL_SRCS)) \
                       $(patsubst %.S,$(BUILDDIR)/startup/%.o,$(STARTUP_SRCS))

ELF                 := $(BUILDDIR)/$(PROJ_NAME).elf
HEX                 := $(BUILDDIR)/$(PROJ_NAME).hex
MCS                 := $(BUILDDIR)/$(PROJ_NAME).mcs
ASM                 := $(BUILDDIR)/$(PROJ_NAME).asm
VMEM                := $(BUILDDIR)/$(PROJ_NAME).v
EELF                := $(BUILDDIR)/$(PROJ_NAME).eelf

# ── ISA and flag assembly ─────────────────────────────────────────────────
MABI                := ilp32
MARCH               := rv32i
ifeq ($(MULDIV),yes)
    MARCH := $(MARCH)m
endif
ifeq ($(COMPRESSED),yes)
    MARCH := $(MARCH)ac
endif

CFLAGS  := -Wall -march=$(MARCH) -mabi=$(MABI) \
           -ffunction-sections -fdata-sections -fstrict-volatile-bitfields \
           -MD -O1
ifeq ($(BENCH),yes)
    CFLAGS += -fno-inline
endif

LDFLAGS := -march=$(MARCH) -mabi=$(MABI) -mcmodel=medany \
           -nostdlib -nostartfiles -ffreestanding \
           -Wl,--gc-sections \
           -Wl,-Bstatic,-T,$(LDSCRIPT),-Map,$(BUILDDIR)/$(PROJ_NAME).map,--print-memory-usage \
           -lm -lgcc -lc_nano

INC     := -I$(HEADER_DIR) $(foreach d,$(USER_DIRS),-I$(d))

# ── Version stamp (git-aware; falls back cleanly if no git available) ─────
GIT_SHORTREV      := $(shell git -C $(WORKSPACE) rev-parse --short HEAD 2>/dev/null || echo nogit)
GIT_DIRTY         := $(shell git -C $(WORKSPACE) diff --quiet HEAD -- 2>/dev/null || echo -dirty)
TIME_STR          := $(shell date "+%F %T")
VSTRING           := "$(GIT_SHORTREV)$(GIT_DIRTY)|$(TIME_STR)"

# ── Rules ─────────────────────────────────────────────────────────────────
.PHONY: all clean
.SECONDARY: $(OBJS)

all: $(HEX) $(MCS) $(ASM) $(VMEM)

$(ELF): $(OBJS) $(RUNTIME_OBJS) | $(BUILDDIR)
	$(RISCV_CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

$(BUILDDIR)/%.o: $(WORKSPACE)/%.c | $(BUILDDIR)
	@mkdir -p $(dir $@)
	$(RISCV_CC) -c $(CFLAGS) $(INC) -DTD_GW1NR_9_C7I6 \
	    -DVERSION=$(VSTRING) -DSTACK_SIZE_$(STACK_SIZE_BYTES) \
	    -o $@ $<

$(BUILDDIR)/%.o: $(WORKSPACE)/%.S | $(BUILDDIR)
	@mkdir -p $(dir $@)
	$(RISCV_CC) -c $(CFLAGS) -D__ASSEMBLY__=1 -o $@ $<

$(BUILDDIR)/startup/%.o: %.S | $(BUILDDIR)
	@mkdir -p $(dir $@)
	$(RISCV_CC) -c $(CFLAGS) -D__ASSEMBLY__=1 -o $@ $<

$(BUILDDIR)/local/%.o: %.c | $(BUILDDIR)
	@mkdir -p $(dir $@)
	$(RISCV_CC) -c $(CFLAGS) $(INC) -DTD_GW1NR_9_C7I6 \
	    -DVERSION=$(VSTRING) -DSTACK_SIZE_$(STACK_SIZE_BYTES) \
	    -o $@ $<

%.hex: %.elf
	$(RISCV_OBJCOPY) -O ihex $< $@

%.bin: %.elf
	$(RISCV_OBJCOPY) -O binary $< $@

%.v: %.elf
	$(RISCV_OBJCOPY) -O verilog $< $@

%.asm: %.elf
	$(RISCV_OBJDUMP) -S -d $< > $@

%.mcs: %.hex
	cp $< $@

$(BUILDDIR) $(ARTEFACTDIR):
	@mkdir -p $@

clean:
	rm -rf $(BUILDDIR)
