# -*- mode: python ; coding: utf-8 -*-
# build.spec — NuncaAcaboLosJuegos (PyInstaller)
# Build: pyinstaller build.spec

from PyInstaller.utils.hooks import collect_data_files

# Temas/JSON de CustomTkinter deben viajar junto al .exe (si no, la GUI
# falla al arrancar porque no encuentra sus assets).
ctk_datas = collect_data_files("customtkinter")

a = Analysis(
    ["src/main.py"],
    pathex=[],
    binaries=[],
    datas=ctk_datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="NuncaAcaboLosJuegos",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # windowed: sin ventana de consola
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
