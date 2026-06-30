# Default hardware overlay (ELM11-Feather)

Place the default overlay image here as **`emblua.vg`**.

When a user creates a new Lua workspace targeting **ELM11-Feather** *without*
ticking *Custom Hardware Overlay*, the IDE copies this `emblua.vg` into the
workspace as `hardware/.build/emblua.vg` so the project can be synthesised
straight away (see `HardwareOverlayPanel.deploy_default_overlay`).

This should be the 66 MHz overlay, to match the default `timing.sdc` that the
build templates deploy. If you need a different frequency, add a `timing.sdc`
here too and it will override the build-template default.

Both files are bundled into packaged builds by `packaging/arvore.spec`.
