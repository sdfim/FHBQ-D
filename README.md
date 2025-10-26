# FHBQ-D: Command Line Control for Heat Recovery Ventilators

This project provides a simple Python command-line interface to control FHBQ-D series Heat Recovery Ventilators (HRVs) found in units from manufacturers like Cooper & Hunter (C&H), Gree, and others, via the RS485 communication bus.

The implementation is based on reverse-engineering the protocol used by the control panel.

> ⚠️ Disclaimer
>
> Use this software at your own risk. Improper use may result in damage to your ventilation unit. The authors are not responsible for any damage or malfunctions that may occur.

## Compatibility

This tool is designed to work with units whose control board resembles the pictured board in the repository. If your board looks similar, you can proceed with testing.
![board](https://github.com/sdfim/FHBQ-D/blob/master/img/board.jpg)

## Prerequisites

- Python 3
- pyserial (install with `pip install pyserial`)
- USB → RS485 converter (physical interface to connect your computer, e.g. Raspberry Pi, to the HRV control board)

## Hardware connection

The HRV control board typically has two communication ports: `COM-MANUAL` and `COM-UNION`.

- One of these ports is used by the standard remote control panel.
- Connect the USB-RS485 converter to the remaining unused port.

Wiring:

- Connect the `A` terminal on the USB-RS485 converter to the `A` terminal on the control board port.
- Connect the `B` terminal on the USB-RS485 converter to the `B` terminal on the control board port.

Note: Ensure the serial device path in the script (default `/dev/ttyUSB0`) matches the port assigned to your converter.

## Usage

The control script is named `recuperator_cli.py`. It accepts commands as arguments, translates them into the appropriate RS485 packet, and sends them to the unit.

Run with `python3 recuperator_cli.py <command>`.

### 1) View help

To see a list of available operation modes, speeds and bypass options:

```
python3 recuperator_cli.py help
```

### 2) Check current status

To quickly view the current operating mode, fan speed and bypass state:

```
python3 recuperator_cli.py status
```

Example output (silent mode):

```
mode: normal; speed: 3; bypass: auto;
```

### 3) Set operating mode (three-part command)

The most common command format is a three-part structure:

```
<mode> <speed> <bypass>
```

- Part: Mode — operation mode type
  - Examples: `n` (Normal), `s` (Save / Eco), `ne` (Normal Exhaust), `ss` (Save Supply), etc.
- Part: Speed — fan speed level
  - Values: `1`, `2`, `3`
- Part: Bypass — bypass operation
  - Values: `auto`, `on`, `off`

Example 1 — Set Normal mode, speed 3, bypass automatic:

```
python3 recuperator_cli.py n 3 auto
```

Example 2 — Set Save mode, speed 1, bypass ON:

```
python3 recuperator_cli.py s 1 on
```

### 4) Special one-word commands

- `off` — completely turn the recuperator unit off
- `rhon` — enable the relative humidity control function
- `rhoff` — disable the relative humidity control function

Example:

```
python3 recuperator_cli.py off
```

### 5) Send raw hex packet (advanced)

For advanced users and debugging, you can send a raw hexadecimal string representing the data bytes (excluding checksum). The string below is a 34-character example (17 data bytes):

```
python3 recuperator_cli.py h 7e7ec0ff110b0740028a214064200d00
```
