# -*- mode: python ; coding: utf-8 -*-


import PyInstaller.config
PyInstaller.config.CONF['workpath'] = "./engine-prebuild/tripy_linux"
PyInstaller.config.CONF['distpath'] = "./engine/"
PyInstaller.config.CONF['warnfile'] = "./engine-prebuild/tripy_linux/warn-tripy_linux"
PyInstaller.config.CONF['xref-file'] = "./engine-prebuild/tripy_linux/xref-tripy_linux"
block_cipher = None

_bin_dirpath = 'bin/linux'
imaging_engines = [(branch[1], os.path.dirname(os.path.join(_bin_dirpath, branch[0]))) for branch in Tree(_bin_dirpath)]
added_files = [
    ('config/engine.toml', 'config/'),
]
added_files.extend(imaging_engines)
a = Analysis(['main.py'],
             pathex=['.'],
             binaries=[],
             datas=added_files,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='tridentengine',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='linux')
