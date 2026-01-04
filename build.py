import PyInstaller.__main__
import os
import shutil

# Clean previous builds
if os.path.exists('build'):
    shutil.rmtree('build')
if os.path.exists('dist'):
    shutil.rmtree('dist')

# Determine separator for add-data based on OS
# On Windows it's ';', on Unix it's ':'
sep = ';' if os.name == 'nt' else ':'

print(f"Building for OS: {os.name}")

PyInstaller.__main__.run([
    'src/main.py',                       # Entry point
    '--name=VLCM_Reg_Tool',              # Name of executable
    '--onefile',                         # Single file bundle
    '--clean',                           # Clean cache
    f'--add-data=config.json{sep}.',     # Include config.json
    f'--add-data=src{sep}src',           # Include source folder (for any dynamic loading)
    
    # Hidden imports often missed by PyInstaller for these libs
    '--hidden-import=src',
    '--hidden-import=src.utils',
    '--hidden-import=src.utils.ocr',
    '--hidden-import=src.utils.audio',
    '--hidden-import=transformers',
    '--hidden-import=torch',
    '--hidden-import=PIL',
    '--hidden-import=patchright',

    # Collect heavy dependencies explicitly if needed (usually handled by hooks but being safe)
    '--collect-all=transformers',
    '--collect-all=patchright',
    '--collect-all=openai_whisper',
])

print("Build Complete. Executable is in 'dist/VLCM_Reg_Tool/'")
