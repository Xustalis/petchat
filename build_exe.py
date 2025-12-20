"""Build script for creating executable"""
import os
import sys
import shutil
from pathlib import Path


def build_with_pyinstaller():
    """Build executable using PyInstaller"""
    print("Building with PyInstaller...")
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--name=pet-chat",
        "--onefile",
        "--windowed",  # No console window
        "--icon=NONE",  # Add icon file path if you have one
        "--add-data=config;config",  # Include config directory
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtGui",
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=openai",
        "--hidden-import=sqlalchemy",
        "--hidden-import=dotenv",
        "--collect-all=PyQt6",
        "main.py"
    ]
    
    os.system(" ".join(cmd))
    print("\nBuild complete! Executable is in dist/ directory")


def build_with_nuitka():
    """Build executable using Nuitka (as specified in PRD)"""
    print("Building with Nuitka...")
    
    # Nuitka command
    cmd = [
        "python", "-m", "nuitka",
        "--standalone",
        "--onefile",
        "--windows-disable-console",  # No console window on Windows
        "--enable-plugin=pyqt6",
        "--include-package-data=config",
        "--include-package-data=core",
        "--include-package-data=ui",
        "--output-dir=dist",
        "--output-filename=pet-chat.exe",
        "main.py"
    ]
    
    os.system(" ".join(cmd))
    print("\nBuild complete! Executable is in dist/ directory")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        method = sys.argv[1]
    else:
        method = "pyinstaller"  # Default to PyInstaller
    
    if method == "nuitka":
        build_with_nuitka()
    else:
        build_with_pyinstaller()

