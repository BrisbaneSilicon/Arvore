# Arvore

Arvore is the IDE for the [ELM11](https://brisbanesilicon.com.au/elm11/) and [ELM11-Feather](https://brisbanesilicon.com.au/elm11-feather/) Microcontroller boards by [BrisbaneSilicon](https://brisbanesilicon.com.au/).
<br><br>

<p align="center">
<img src="https://github.com/BrisbaneSilicon/Arvore/blob/master/img/hw_overlay_img.png" width="75%">
<br><em>Selecting and installing a custom 'Hardware Overlay'</em>
</p>
<br><br>

## Table of Contents

*   [Overview](#overview)
*   [Getting Started](#getting-started)
    *   [Prerequisites](#prerequisites)
    *   [License Setup](#license-setup)
        *   [Public License Servers](#public-license-servers)
    *   [Initial Setup](#initial-setup)
*   [Workspaces](#workspaces)
*   [Hardware Overlay](#hardware-overlay)
*   [Code Editor](#code-editor)
*   [REPL](#repl)
*   [Command Mode](#command-mode)
<br><br>

## Overview

The Arvore IDE provides a graphical user interface for developing with the ELM11 and ELM11-Feather Microcontroller boards. It features the following:

* A simple workspace abstraction for organizing modules into a single, unified project (see [Workspaces](#workspaces)).
* A mode for selecting and installing a ‘Hardware Overlay’ (see [Hardware Overlay](#hardware-overlay)).
* A standard code editor for software or firmware development at any of the Application, Driver or Hardware layers (see [Code Editor](#code-editor)).
* A dynamic runtime mode in which it can be connected to the ELM11 or ELM11-Feather boards via USB-UART, for the purposes of uploading Application, Driver or Hardware layer modules, or interacting with the boards’ REPL.
<br><br>

## Getting Started

First, fulfill the below pre-requisites then complete the steps detailed in [Initial Setup](#initial-setup).

### Prerequisites

1. A PC running an x64 compatible, Debian-based flavour of Linux or Windows 11.
   - Other flavours of Linux may work but aren't officially supported.
   - We recommend [Ubuntu](https://ubuntu.com/).
2. Either install a pre-built [binary](https://github.com/BrisbaneSilicon/Arvore/tree/master/bin/) or a copy of this repository (`git clone https://github.com/BrisbaneSilicon/Arvore.git`).
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
   

### License Setup

There are two options (both free) for licensing GOWIN EDA.
1. Using a local license file.
2. Using a floating license server.

Option (1) requires applying for a license from GOWIN [here](https://www.gowinsemi.com/en/support/license/). It can take up to a few working days for GOWIN to provide you with a license, which will be valid for a period of one year. Option (2) requires the same initial step if you wish to host your own license server. Alternatively you can point the GOWIN license manager at a public license server; this is likely the quickest path forwards. See [Public License Servers](#public-license-servers) for a list of public license servers.

#### Linux

Launch a bash terminal and perform the following:

1. Change directory to the GOWIN IDE installation 'bin' directory.
   - `cd <GOWIN IDE install directory>/IDE/bin/`
2. Run the licensing manager.
   - `./license_config_gui`
   - Alternatively you can run the GOWIN IDE `./gw_ide` and click 'Help' - 'Manage License'.
3. Either point the licensing manager at your local license file (Option 1 above) or a floating license server.
4. Press 'Check' to validate the license.
   - If the license has been successfully validated, it should produce a popup window __INFO__ with the message __Server is OK__.
5. Click 'Save' to save your license setup.
<br>

> [!WARNING]
> Sometimes the first license check (step 4) will fail - simply repeat the step to validate the license.

#### Windows

To configure the license on Windows GOWIN EDA:

1. Open GOWIN EDA (`gw_ide.exe`) from your install directory.
2. Click 'Help' - 'Manage License'.
3. Either point the licensing manager at your local license file (Option 1 above) or a floating license server.
4. Press 'Check' to validate the license.
   - If the license has been successfully validated, it should produce a popup window __INFO__ with the message __Server is OK__.
5. Click 'Save' to save your license setup.
<br>

> [!WARNING]
> Sometimes the first license check (step 4) will fail - simply repeat the step to validate the license.

#### Public License Servers

A list of public GOWIN EDA license servers is below. These are community reported and might not be official or stable (see the previous instructions on how to check their validity).

| IP Address | Port |
| :------: | :------: |
| 106.55.34.119 | 10559 |
| 43.128.7.128 | 10559 |

<br>

### Initial Setup

1. Launch the Arvore IDE.
2. Navigate to 'Tools' -> 'Settings'.
3. If you are planning on extending the 'Driver Layer', setup the 'Compiler Path' in the 'C' tab.
4. If you are planning on building your own 'Hardware Overlay', setup the following in the 'Hardware' tab:
   - The 'Gowin IDE Path'.
   - If you're using Linux, setup the 'libfreetype.so' path (typically '/lib/x86_64-linux-gnu/libfreetype.so').
   - If you're using Linux, setup the 'libz.so.1' path (typically '/lib/x86_64-linux-gnu/libz.so.1').
   - Potentially (likely only required on Linux) setup the 'Pre-program command' (to remove a loaded FTDI driver, i.e. 'pkexec modprobe -r ftdi_sio').
   - Configure the remainder of the tabs as required.
5. Modify the theme ('View' -> 'Theme') as desired.
<br><br>

## Workspaces

The 'Workspace' abstraction allows the user to organise modules into a single, unified project. It also allows different projects to be separated, and rapidly retrieved upon IDE launch.

To create a workspace, simply select (or create) a target workspace folder in the directory tree at left, right-click it and select 'New Workspace'.

<p align="center">
<img src="https://github.com/BrisbaneSilicon/Arvore/blob/master/img/workspace_creation.png" width="75%">
<br><em>Workspace creation</em>
</p>
<br>

A popup will then appear, allowing you to tailor the new workspace as per your target board and usage.<br>

<p align="center">
<img src="https://github.com/BrisbaneSilicon/Arvore/blob/master/img/workspace_configuration.png" width="25%">
<br><em>Workspace settings</em>
</p>
<br>

These fields can be described as follows:

| Field | Description |
| :------: | :------: |
| Target Board | Set the workspace target board to either ELM11 or ELM11-Feather |
| Language Mode | Set the top-level language mode to either 'Lua' or 'C'. If 'C', no REPL usage is permitted. |
| Default HDL | Set the HDL used as part of the Hardware Layer to either 'SystemVerilog' or 'VHDL' |
| Customize Hardware Overlay | Install a custom hardware overlay instead of the default (will launch 'Hardware Overlay Config' mode - see below) |

When a new workspace is created, it is populated with a default, example project, that demonstrates usage of each of the three programmable layers.

<br><br>

## Hardware Overlay

The Arvore IDE offers a mode, 'Hardware Overlay Config', that allows the user to select and install a custom Hardware Overlay. This mode can be enabled by selecting 'View' - 'Hardware Overlay Config' or by pressing 'F1'. The default view in this mode is a list of available Hardware Overlays, upon which the user can search based on its available features. The user can also filter on whether the Hardware Overlay has been downloaded (the full set of Hardware Overlays are hosted by BrisbaneSilicon, and are constantly being added to and updated). If a visual diagram of a Hardware Overlay is desired, the user can simply click the 'Diagram' button in the top right. See the image at the beginning of this README for an example of the 'Hardware Overlay Config' mode.
<br><br>

## Code Editor

The Arvore IDE naturally offers a code editor which allows the user to program at any of the Application, Driver or Hardware Layers. See the following diagram:

<p align="center">
<img src="https://github.com/BrisbaneSilicon/Arvore/blob/master/img/code_editor.png" width="75%">
<br><em>Code editor</em>
</p>
<br>

The user can also build and upload any of the Layer artefacts to the board, as per the following buttons:

| Button | Description |
| :------: | :------: |
| Upload | Upload the active (i.e. selected) Application Layer file (Lua) to the board |
| Run | Run the active Application Layer file on the board |
| Stop | Stop any running application on the board |
| Build | Build the Driver Layer |
| Clean | Clean the Driver Layer |
| Flash | Flash the Driver Layer to the board |
| Synth | Synthesize the Hardware Layer |
| Clean | Clean the Hardware Layer |
| Program | Program the Hardware Layer to the board |

<br><br>

## REPL

## Command Mode


