# Sample C/C++ modules

This directory hosts a small embedded-style brake controller with shared features:
`brake`, `can`, `timing`, `diagnostics`, `error_handling`, `safety`, `calibration`,
`nvm`, `init`, and `comms`.

Modules:
- `brake_controller`: core brake control logic, safety interlocks, timing updates.
- `can_if`: CAN comms interface for brake status and diagnostics frames.
- `diag`: diagnostics and error handling.
- `nvm_store`: NVM calibration storage.
- `init.c`: system init sequence.

These files are illustrative and do not include a build system.
