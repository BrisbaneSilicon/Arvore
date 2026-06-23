import sys
import os

def endianess_swap(word):
    word_es = ((word << 24) & 0xFF000000)
    word_es |= ((word << 8) & 0xFF0000)
    word_es |= ((word >> 8) & 0xFF00)
    word_es |= ((word >> 24) & 0xFF)

    return word_es

def lfsr_8bit_next(byte):
    byte_next = (byte << 1) & 0xFF
    byte_next |= (((byte & 0x80) >> 7) ^ ((byte & 0x20) >> 5) ^ ((byte & 0x10) >> 4) ^ ((byte & 0x8) >> 3))

    return byte_next

def lfsr_16bit_next(word):
    word_next = (word << 1) & 0xFFFF
    word_next |= (((word & 0x8000) >> 15) ^ ((word & 0x4000) >> 14) ^ ((word & 0x1000) >> 12) ^ ((word & 0x8) >> 3))

    return word_next

def lfsr_32bit_next(word):
    word_next = (word << 1) & 0xFFFFFFFF
    word_next |= (((word & 0x80000000) >> 31) ^ ((word & 0x200000) >> 21) ^ ((word & 0x2) >> 1) ^ ((word & 0x1) >> 0))

    return word_next

def lfsr_32bit_next_alt(word):
    word_next = (word << 1) & 0xFFFFFFFF
    word_next |= (((word & 0x800000) >> 23) ^ ((word & 0x200000) >> 21) ^ ((word & 0x80) >> 7) ^ ((word & 0x1) >> 0))

    return word_next

def encrypt(word, address):
    i_rd_data_mmsb_lfsr8 = lfsr_8bit_next(address >> 16)
    i_rd_data_mlsb_lfsr8 = lfsr_8bit_next(address >> 12)
    i_rd_data_lfsr32 = lfsr_32bit_next_alt(address | 0x18000001)

    tmp = lfsr_16bit_next((i_rd_data_mmsb_lfsr8 << 8) | i_rd_data_mlsb_lfsr8)
    tmp2 = lfsr_16bit_next((i_rd_data_lfsr32 >> 2) & 0xFFFF)
    enc_word = tmp << 16 | tmp2

    word_as_int = int(word, 16)
    word_as_int_le = endianess_swap(word_as_int)

    word_enc = word_as_int_le ^ enc_word
    if (address & 0x4) == 0:
        if (address & 0x8) == 0:
            word_enc ^= 0xdeadbeef
        else:
            word_enc ^= 0x8badf00d
    else:
        if (address & 0x8) == 0:
            word_enc ^= 0x99abcdef
        else:
            word_enc ^= 0x44332211

    word_enc_be = endianess_swap(word_enc)

    word_enc_be_as_hex = hex(word_enc_be)[2:]
    while len(word_enc_be_as_hex) < 8:
        word_enc_be_as_hex = '0' + word_enc_be_as_hex

    return bytes.fromhex(word_enc_be_as_hex)

if __name__ == '__main__':
    if len(sys.argv) != 4 or '-h' in sys.argv:
        print("Usage: python eelf.py <elf file> <output filename> <start address>")
        sys.exit()

    elf_file_fullpath = sys.argv[1]
    elf_file = open(elf_file_fullpath, 'rb')
    eelf_file = open(sys.argv[2], 'wb')

    code_start_address = int(sys.argv[3], 16)

    # NOTE: locate start of instructions

    try:
        addr = code_start_address
        code_started = False
        while True:
            word = elf_file.read(4)
            word_as_hex = word.hex()
            if word_as_hex == '6f00000a':
                code_started = True

            if code_started:
                eelf_file.write(encrypt(word_as_hex, addr))

                addr = addr + 4
            else:
                eelf_file.write(word)
    except Exception as e:
        pass
