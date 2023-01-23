# linux / macos: compile to ~/.cache
# windows: compile to C:\Windows\Temp

# Parse header

# Fill cpp file

# Compile and copy files to user's Extensions dir

import sys
import os
import platform
import shutil
import re

def parseHeader(kronosHeaderFile: str):
    ins = 1
    outs = 1
    bufsNames = []
    bufsParams = []
    paramsNames = []

    # First pass: ins / outs and buffers (they don't interact with each other)
    insToken = "typedef float KronosaudioInputType["
    outsToken = "typedef float KronosOutputType["
    bufInputTypeToken = "InputType["
    for item in kronosHeaderFile.split("\n"):
        # ins
        if insToken in item:
            insStr = item.replace(insToken, "")
            insIdx = insStr.rfind("];")
            ins = int(insStr[:insIdx])

        # outs
        if outsToken in item:
            outsStr = item.replace(outsToken, "")
            outsIdx = outsStr.rfind("];")
            outs = int(outsStr[:outsIdx])

        # Buffers    
        if bufInputTypeToken in item and insToken not in item:
            bufName = item.replace("typedef float Kronos", "")
            inputTypeIdx = bufName.rfind(bufInputTypeToken)
            bufName = bufName[:inputTypeIdx].lower()
            bufsNames.append(bufName)
            bufsParams.append(bufName + "samplerate")
            bufsParams.append(bufName + "size")
            bufsParams.append(bufName + "frames")
            bufsParams.append(bufName + "numchans")

    # Params (they need buffers to be done)
    kronosSetToken = "static void KronosSet"
    kronosInstancePtrToken = "(KronosInstancePtr instance, const float*"
    for item in kronosHeaderFile.split("\n"):
        if kronosSetToken and kronosInstancePtrToken  in item:
            paramName = item.replace(kronosSetToken, "")
            kronosInstancePtrIdx = paramName.rfind(kronosInstancePtrToken)
            paramName = paramName[:kronosInstancePtrIdx].lower()
            if paramName not in bufsParams: # Exculde buffer params
                paramsNames.append(paramName)
    
    return (ins, outs, paramsNames, bufsNames)

def main() -> int:
    # Check file exists and extract name
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
    kc = "kc -O 3 -H ./" + headerFile + " -P Kronos " + kronosFile
    if (os.system(kc) != 0):
        return 1

    with open(headerFile, "r") as text_file:
        kronosHeaderFile = text_file.read()

    (ins, outs, params, buffers) = parseHeader(kronosHeaderFile)

    print("ins:", ins)
    print("outs:", outs)
    print("params:", params)
    print("buffers:", buffers)

    return 0

if __name__ == '__main__':
    sys.exit(main())