# Arvore

Arvore is the IDE for the [ELM11](https://brisbanesilicon.com.au/elm11/) and [ELM11-Feather](https://www.crowdsupply.com/brisbanesilicon/elm11-feather) Microcontroller boards by [BrisbaneSilicon](https://brisbanesilicon.com.au/).

<br><br>

## Table of Contents

*   [Overview](#overview)
*   [Getting Started](#getting-started)
    *   [Prerequisites](#prerequisites)

<br><br>

## Overview

<br><br>

## Getting Started

Fulfill the below pre-requisites.

### Prerequisites

1. A PC running an x64 compatible, Debian-based flavour of Linux or Windows 11.
   - Other flavours of Linux may work but aren't officially supported.
   - We recommend [Ubuntu](https://ubuntu.com/).
2. Either a pre-built [binary](https://github.com/BrisbaneSilicon/Arvore/tree/master/bin/) or a copy of this repository (`git clone https://github.com/BrisbaneSilicon/Arvore.git`).
   - If you are planning on running the IDE from source, you will require the following:
       - Python>=3.12.3
       - PyQt6>=6.4.0
       - pyserial
4. If you are planning on extending the 'Driver Layer', an installation of the [RISC-V GCC toolchain](https://github.com/xpack-dev-tools/riscv-none-elf-gcc-xpack).
5. If you are planning on building your own 'Hardware Overlay', or extending the 'Hardware Layer', an installation of GOWIN EDA V1.9.12.
   - Available from the official GOWIN EDA [download page](https://www.gowinsemi.com/en/support/download_eda/) or via direct links, [Linux](https://cdn.gowinsemi.com.cn/Gowin_V1.9.12_linux.tar.gz) [Windows](https://cdn.gowinsemi.com.cn/Gowin_V1.9.12_x64_win.zip).
   - You may need to first register as a GOWIN member [here](https://www.gowinsemi.com/en/member/).
   - On Linux, please ensure that GOWIN EDA is installed to one of the following directories (or be prepared to modify the build script):
     - `$HOME/Applications` `/opt/gowin` `/opt/GOWIN` `/opt/Gowin` `$HOME/Documents/Applications/`
   - On Windows, please ensure that GOWIN EDA is installed to one of the following directories (or be prepared to modify the build script):
      - `C:\Gowin`, `C:\Program Files\Gowin`
   - A free license for GOWIN EDA. See section [License Setup](#license-setup) below.
   

## License Setup

There are two options (both free) for licensing GOWIN EDA.
1. Using a local license file.
2. Using a floating license server.

Option (1) requires applying for a license from GOWIN [here](https://www.gowinsemi.com/en/support/license/). It can take up to a few working days for GOWIN to provide you with a license, which will be valid for a period of one year. Option (2) requires the same initial step if you wish to host your own license server. Alternatively you can point the GOWIN license manager at a public license server; this is likely the quickest path forwards. See [Public License Servers](#public-license-servers) for a list of public license servers.

<br><br>
