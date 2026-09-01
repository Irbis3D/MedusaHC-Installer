# MedusaHC Installer

A small, standalone terminal application for installing and maintaining the
independent MedusaHC components.

The application is only a launcher. Installation, update, removal, backup and
configuration logic remains in each component's own repository and is updated
together with that component.

## Components

- MedusaHC Core
- MedusaHC Calibration
- MedusaHC Control Panel
- MedusaHC Mainsail

## Install

```bash
cd ~
git clone https://github.com/Irbis3D/MedusaHC-Installer.git medusahc-installer
./medusahc-installer/medusahc-installer.sh
```

Run it again later with the same final command. The launcher is not a service,
does not run in the background, and is not registered in Moonraker Update
Manager.

## Design rules

- Run as the normal printer user, never as root.
- Ask for confirmation before invoking a component installer.
- Enforce component dependencies before installation or update.
- Never duplicate installation logic from component repositories.
- Never edit printer or Moonraker configuration directly.
- Removing the launcher does not remove installed MedusaHC components.

## Remove the launcher

Remove only its directory:

```bash
rm -rf ~/medusahc-installer
```

This does not uninstall or modify any MedusaHC component.
