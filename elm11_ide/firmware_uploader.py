import serial, sys
import time
import datetime

enable_upload_delay = False

def isp_wait_byte(ser, exbyte):
    resp = bytes([])
    while len(resp) == 0:
        resp = ser.read()
    
    return resp[0] == exbyte, resp[0]
    

def isp_exec_esec(ser, addr):
    # ISP Flasher ESEC (Erase Sector)
    # Host:  0x30        addr2-0
    # Reply:       0x31           [erase] 0x32 
    
    saddr = bytes([(addr // 65535) & 0xFF, (addr // 256) & 0xF0, 0x00])

    ser.write(bytes([0x30]))
    isp_wait_byte(ser, 0x31)
    
    ser.write(saddr)
    isp_wait_byte(ser, 0x32)

def isp_exec_wbuf(ser, data):
    # ISP Flasher WBUF (Write Pagebuf)
    # Host:  0x10        len dat0-datn
    # Reply:       0x11                chk 
    wrbytes = bytes([len(data) - 1] + data)
    chksum = sum(data) & 0xFF
    
    ser.write(bytes([0x10]))
    isp_wait_byte(ser, 0x11)

    if enable_upload_delay:
        for b in wrbytes:
            ser.write(bytes([b]))
            time.sleep(0.0001)
    else:
        ser.write(wrbytes)

    chksumPass, rxval = isp_wait_byte(ser, chksum)
    if not chksumPass:
        print("  Bad chksum", rxval)
        return False

    return True

def isp_exec_wpag(ser, addr):
    # ISP Flasher WPAG (Write Page)
    # page length saved from last WBUF
    # Host:  0x40        addr2-0
    # Reply:       0x41           [program] 0x42
    pgbuf = bytes([(addr // 65535) & 0xFF, (addr // 256) & 0xFF, addr & 0xFF])

    ser.write(bytes([0x40]))
    isp_wait_byte(ser, 0x41)

    ser.write(pgbuf)
    pageWrPass, rxval = isp_wait_byte(ser, 0x42)
    if not pageWrPass:
        print(" - Page write failed! Exit.")
        sys.exit()


def isp_exec_rst(ser):
    # ISP Flasher RST
    # Host:  0xF0       
    # Reply:       0xF1 
    ser.write(bytes([0xF0]))
    ser.read()

if __name__ == '__main__':
    if len(sys.argv) < 4 or '-h' in sys.argv:
        print("Usage: python pico-programmer.py FIRMWARE_FILE_PATH SERIAL_PORT SERIAL_PORT_BAUD [PAGE_WRITE (default=True)] [SECTOR_ERASE (default=True)]")
        sys.exit()

    print("Firmware updater begin")
        
    # read file
    filepath = sys.argv[1]
    file = open(filepath, 'r', buffering=8192)

    lprog = []
    plinecount = 0

    lbegin = False
    for line in file:
        # skipping ram space
        line = line.strip();
        if lbegin:
            lprog.append(line)
            plinecount += 1
        if line.startswith('@00000000'):
            lbegin = True
            lprog.append(line)

    file.close()

    if len(sys.argv) > 4:
        page_write = (sys.argv[4] == "True")
    else:
        page_write = True

    if len(sys.argv) > 5:
        erase_sector = (sys.argv[5] == "True")
    else:
        erase_sector = True


    nproglen = 16 * (plinecount-1) + len(lprog[plinecount-1].split(' '))

    print("Read program with", nproglen, "bytes")

    prog = [0] * nproglen
    wp = 0
    flash_base = 0x00000000

    for i, lstr in enumerate(lprog):
        if lstr.startswith('@'):
            wp = int(lstr[1:], 16) - flash_base
        else:
            for j, bprog in enumerate(lstr.split(' ')):
                prog[wp] = int(bprog, 16)
                wp += 1


    # open serial and check status
    ser = serial.Serial(sys.argv[2], sys.argv[3], timeout=0.01)

    serial_port_baud = int(sys.argv[3])
    if serial_port_baud <= 115200:
        enable_upload_delay = True

    print("  - Attempt to establish comms with firmware updater -", flush=True)
    print('    ', end='', flush=True)

    ack_count = 0
    for i in range(100):
        ser.reset_input_buffer()
        ser.write(bytes([0x07]))
        ser.flush()
        
        time.sleep(0.02)

        res = ser.read()

        if i % 10 == 0:
            print('.', end='', flush=True)
        
        if len(res) > 0 and res[0] == 0x06:
            ack_count = ack_count + 1
            if ack_count > 20:
                break

    print("")

    if len(res) == 0 or res[0] != 0x06:
        print("Failed to establish comms with firmware updater")
        print("Please power cycle board with user-button pressed")
        ser.close()
        sys.exit()
    else:
        print("Comms established.")

    # NOTE: flush buffer...
    print("Flush RX buffer...", end='', flush=True)
    for i in range(100):
        ser.read()
    print("done")


    # begin programming
    sectind = 0
    pageind = 0
    wrtbyte = 0
    rembyte = len(prog)
    curraddr = 0
    pagestep = 256

    sectreq = ((rembyte - 1) // 4096) + 1
    pagereq = ((rembyte - 1) // pagestep) + 1

    print("Begin firmware upload")
    print("Total sectors", sectreq, flush=True)
    print("Total pages", pagereq, flush=True)

    wbufFailed = False
    wbufRetryLimit = 3

    printDuration = False

    for i in range(sectreq):
        if printDuration:
            fstart = datetime.datetime.now()

        print(f"Flashing {i+1} / {sectreq}", end='', flush=True)

        if erase_sector:
            # NOTE: erase the sector to be programmed

            isp_exec_esec(ser, curraddr)
        
        for j in range( min(16, pagereq - i*16) ):
            wlen = min(pagestep, rembyte - curraddr)
            wrdat = prog[curraddr:curraddr+wlen]
            
            # NOTE: send data to page buffer

            wbufRetryCnt = 0
            while True:
                if isp_exec_wbuf(ser, wrdat):
                    break
                else:
                    wbufRetryCnt += 1
                    if wbufRetryCnt > wbufRetryLimit:
                        wbufFailed = True
                        break
            if wbufFailed:
                break
            
            if page_write:
                # NOTE: write from page buffer to flash
                isp_exec_wpag(ser, curraddr)
            
            curraddr += pagestep

            print('.', end='', flush=True)
        
        if wbufFailed:
            print("  Too many retires on sending data to page buffer")        
            break

        if printDuration:
            fend = datetime.datetime.now()
            print("done. took {} seconds.".format(str(fend - fstart)))
        else:
            print("done")

    # reset system
    if wbufFailed:
        print("Flashing failed")
    else:
        isp_exec_rst(ser)

        print("")
        print("Flashing completed")
        print("Address Top = 0x{:x}".format(curraddr))

    ser.close()
