# Source and license scope

The LICENSE in this directory covers the original Python tools, C userspace
shim, configuration templates and build metadata authored for this project.
It does not cover `bfx_wifi_abi_probe.c`, which is GPL-2.0-only as marked in
its SPDX header and MODULE_LICENSE declaration. The GPL version 2 text is at
https://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

The external Linux kernel and RTL8821CU source are not vendored here. Their
licenses remain in the pinned upstream trees listed in reference-target.json;
retain their notices and fulfill their source-distribution requirements if
redistributing a built module. Generated symvers values are target ABI
metadata, not license grants to the upstream code.

OEM APKs, HAL/VNDK binaries, firmware, credentials and signing keys are not
included. Locally supplying a binary does not grant rights to redistribute it.
The TV compile stubs are interface declarations only; no upstream class
implementation is copied into the added DEX.
