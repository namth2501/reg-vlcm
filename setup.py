import subprocess
import sys
import os
import shutil
import platform

def install_requirements():
    print("[-] Installing Python dependencies from requirements.txt...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("[+] Dependencies installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"[!] Failed to install dependencies: {e}")
        sys.exit(1)

def install_browsers():
    print("[-] Installing Patchright browsers...")
    try:
        # Check if patchright is installed first (it should be from step 1)
        subprocess.check_call(["patchright", "install"])
        print("[+] Browsers installed successfully.")
    except Exception as e:
        print(f"[!] Failed to install browsers: {e}")
        print("    Try running 'patchright install' manually.")
        sys.exit(1)

def download_ffmpeg():
    print("[-] Downloading FFmpeg...")
    system = platform.system()
    try:
        import urllib.request
        import zipfile
        import tarfile
        
        if system == "Windows":
            url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
            filename = "ffmpeg.zip"
            print(f"    Downloading from {url}...")
            urllib.request.urlretrieve(url, filename)
            
            print("    Extracting...")
            with zipfile.ZipFile(filename, 'r') as zip_ref:
                # Extract relevant file
                for file in zip_ref.namelist():
                    if file.endswith("bin/ffmpeg.exe"):
                        with zip_ref.open(file) as source, open("ffmpeg.exe", "wb") as target:
                            shutil.copyfileobj(source, target)
                        break
            os.remove(filename)
            print("[+] FFmpeg installed to project root.")
            
        elif system == "Darwin": # MacOS
            url = "https://evermeet.cx/ffmpeg/ffmpeg-release-zip" 
            # Note: This link might change, but evermeet is standard for mac static builds
            # Alternative: check brew? but user wants auto install.
            filename = "ffmpeg.zip"
            print(f"    Downloading from {url}...")
            urllib.request.urlretrieve(url, filename)
            
            print("    Extracting...")
            with zipfile.ZipFile(filename, 'r') as zip_ref:
                zip_ref.extract("ffmpeg")
            
            # Make executable
            os.chmod("ffmpeg", 0o755)
            os.remove(filename)
            print("[+] FFmpeg installed to project root.")

        elif system == "Linux":
            # Static build for linux (often amd64)
            url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
            filename = "ffmpeg.tar.xz"
            print(f"    Downloading from {url}...")
            urllib.request.urlretrieve(url, filename)
            
            print("    Extracting...")
            with tarfile.open(filename, "r:xz") as tar:
                 # Logic to find ffmpeg binary in tar
                 for member in tar.getmembers():
                     if member.name.endswith("/ffmpeg"):
                         member.name = "ffmpeg" # Rename to extract to current dir? 
                         # Simpler: extract and move
                         f = tar.extractfile(member)
                         with open("ffmpeg", "wb") as out:
                             shutil.copyfileobj(f, out)
                         break
            
            os.chmod("ffmpeg", 0o755)
            os.remove(filename)
            print("[+] FFmpeg installed to project root.")
            
        else:
            print(f"[!] Auto-install not supported for OS: {system}")
            return False
            
        return True

    except Exception as e:
        print(f"[!] Failed to download FFmpeg: {e}")
        return False

def check_ffmpeg():
    print("[-] Checking for FFmpeg...")
    if shutil.which("ffmpeg"):
        print("[+] FFmpeg found in PATH.")
    elif os.path.exists("ffmpeg") or os.path.exists("ffmpeg.exe"):
        print("[+] FFmpeg found in current directory.")
    else:
        print("[!] FFmpeg NOT found.")
        print("    Attempting to auto-install FFmpeg...")
        download_ffmpeg()

def main():
    print("=== VLCM Tool Setup ===")
    
    # 1. Install pip requirements
    if os.path.exists("requirements.txt"):
        install_requirements()
    else:
        print("[!] requirements.txt not found!")
        sys.exit(1)
        
    # 2. Install Playwright/Patchright browsers
    install_browsers()
    
    # 3. Check FFmpeg
    check_ffmpeg()
    
    print("\n=== Setup Complete ===")
    print("You can now run the tool using:")
    print("   python -m src.main")

if __name__ == "__main__":
    main()
