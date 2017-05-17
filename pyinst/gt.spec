# -*- mode: python -*-

block_cipher = None

pygcam = '/Users/rjp/bitbucket/pygcam/pygcam'

datas = [
    (pygcam + '/etc/*.*',          'pygcam/etc'),
    (pygcam + '/etc/examples/*.*', 'pygcam/etc/examples'),
    (pygcam + '/builtins/*.py',    'pygcam/builtins'),
]

lib = '/Users/rjp/anaconda/lib'

binaries = []

#excludes = ['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter', 'PyQt5', 'gtk', 'gi']
excludes = ['gtk', 'gi', 'pygcammcs', 'PySide']

import glob

pluginPaths = glob.glob('pygcam/builtins/*_plugin.py')
plugins = map(lambda path: 'pygcam.builtins.' + os.path.splitext(os.path.basename(path))[0], pluginPaths)
hiddenimports = plugins + ['pygcam.sectorEditors', 'pygcam.carbonTax', 'pygcam.constraints']

from pygcam.version import VERSION
import platform

if platform.system() == 'Windows':

    hiddenimports += ['wincom32']
    name = 'gt-' + VERSION + '-win'

else:
    name = 'gt-' + VERSION + '-mac'

    excludes += ['win32con', 'win32com.shell', 'win32com.client', 'win32com.client.gencache',
                'win32clipboard', 'win32evtlog', 'win32evtlogutil', 'win32file', 'win32api',
                'win32pdh', 'win32pipe', 'win32security', 'win32wnet']

    binaries += [('/usr/local/bin/fc-list', '')]
    binaries += [(lib + '/libmkl_avx.dylib', ''),
                 (lib + '/libmkl_avx2.dylib', ''),
                 (lib + '/libmkl_avx512.dylib', ''),
                 (lib + '/libmkl_core.dylib', ''),
                 (lib + '/libmkl_intel.dylib', ''),
                 (lib + '/libmkl_intel_ilp64.dylib', ''),
                 (lib + '/libmkl_intel_lp64.dylib', ''),
                 (lib + '/libmkl_intel_thread.dylib', ''),
                 (lib + '/libmkl_mc.dylib', ''),
                 (lib + '/libmkl_mc3.dylib', ''),
                 (lib + '/libmkl_rt.dylib', ''),
                 (lib + '/libmkl_sequential.dylib', ''),
                 (lib + '/libmkl_vml_avx.dylib', ''),
                 (lib + '/libmkl_vml_avx2.dylib', ''),
                 (lib + '/libmkl_vml_avx512.dylib', ''),
                 (lib + '/libmkl_vml_mc.dylib', ''),
                 (lib + '/libmkl_vml_mc2.dylib', ''),
                 (lib + '/libmkl_vml_mc3.dylib', '')]


a = Analysis(['gt.py'],
             pathex=['/Users/rjp/tmp/pyinst'],
             binaries=binaries,
             datas=datas,
             hiddenimports=hiddenimports,
             hookspath=[],
             runtime_hooks=[],
             excludes=excludes,
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='gt',
          debug=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name=name)
