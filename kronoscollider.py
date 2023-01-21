# linux / macos: compile to ~/.cache
# windows: compile to C:\Windows\Temp

# Parse header

# Fill cpp file

# Compile and copy files to user's Extensions dir]

import sys
import os
import platform
import shutil

def main() -> int:
    # Kronos file stuff
    kronosFile = "~/Sources/KronosBuffer/KronosBuffer.k"
    kronosFile = os.path.abspath(os.path.expanduser(kronosFile))
    if(not os.path.exists(kronosFile)):
        print("ERROR: " + kronosFile + " does not exist")
        return 1
    kronosFileSplit = os.path.splitext(kronosFile)
    name = kronosFileSplit[0].split('/')[-1]

    # mkdir in cache
    if platform.system() == 'Windows':
        cacheKronosCollider = "C:\\Windows\\Temp\\KronosCollider\\"
    else:
        cacheKronosCollider = "~/.cache/KronosCollider/"
    cacheKronosCollider = os.path.expanduser(cacheKronosCollider)
    if(not os.path.exists(cacheKronosCollider)):
        os.mkdir(cacheKronosCollider)

    outDir = cacheKronosCollider + name
    if(os.path.exists(outDir)):
        shutil.rmtree(outDir, ignore_errors=True)
    os.mkdir(outDir)

    # Copy files and cd into it
    cwd = os.getcwd()
    cppFile = cwd + "/cpp/KronosTemplate.cpp"
    cmakeFile = cwd + "/cpp/CMakeLists.txt"
    shutil.copy(kronosFile, outDir)
    shutil.copy(cppFile, outDir)
    shutil.copy(cmakeFile, outDir)
    os.chdir(outDir)

    # Compile kronos code (prefix with Kronos)
    kronosFile = name + ".k"
    headerFile = name + ".h"
    kc = "kc -O 3 -H ./" + headerFile + " -P " + name + " " + kronosFile
    os.system(kc)

    return 0

if __name__ == '__main__':
    sys.exit(main())