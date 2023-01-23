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
    tickAudio = False
    bufsDict = {}
    bufsParams = []
    paramsNames = {}

    # First pass: ins / outs and buffers (they don't interact with each other)
    insToken = "typedef float KronosaudioInputType["
    outsToken = "typedef float KronosOutputType["
    bufInputTypeToken = "InputType["
    kronosHeaderFileSplit = kronosHeaderFile.split("\n")
    for i, item in enumerate(kronosHeaderFileSplit):
        # Audio tick exists
        if "KronosTickAudio" in item:
            tickAudio = True

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
            bufsDict[bufName] = {}
            slotIndex = kronosHeaderFileSplit[i + 2] #*KronosGetValue part of the function
            slotIndex = slotIndex.replace("*KronosGetValue(instance, ", "")
            slotIndexIdx = slotIndex.rfind(") = (void*)")
            slotIndex = int(slotIndex[:slotIndexIdx])
            bufsDict[bufName]["slotIndex"] = slotIndex
            bufsParams.append(bufName + "samplerate")
            bufsParams.append(bufName + "size")
            bufsParams.append(bufName + "frames")
            bufsParams.append(bufName + "numchans")

    # Params (they need buffers to be done)
    kronosSetToken = "static void KronosSet"
    kronosInstancePtrToken = "(KronosInstancePtr instance, const float*"
    for i, item in enumerate(kronosHeaderFileSplit):
        if kronosSetToken and kronosInstancePtrToken in item:
            paramName = item.replace(kronosSetToken, "")
            kronosInstancePtrIdx = paramName.rfind(kronosInstancePtrToken)
            paramName = paramName[:kronosInstancePtrIdx].lower()
            if paramName not in bufsParams: # Exclude buffer params
                slotIndex = kronosHeaderFileSplit[i + 1]
                slotIndex = slotIndex.replace("*KronosGetValue(instance, ", "")
                slotIndexIdx = slotIndex.rfind(") = (void*)")
                slotIndex = int(slotIndex[:slotIndexIdx])
                paramsNames[paramName] = slotIndex
            else: # Add buffer params to existing buf dict
                for param in ["samplerate", "size", "frames", "numchans"]:
                    if param in paramName:
                        bufname = paramName.replace(param, "")
                        slotIndex = kronosHeaderFileSplit[i + 1]
                        slotIndex = slotIndex.replace("*KronosGetValue(instance, ", "")
                        slotIndexIdx = slotIndex.rfind(") = (void*)")
                        slotIndex = int(slotIndex[:slotIndexIdx])
                        bufsDict[bufname]["slotIndex_" + param] = slotIndex
    
    #print(kronosHeaderFile)

    return (tickAudio, ins, outs, paramsNames, bufsDict)

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

    (tickAudio, ins, outs, params, buffers) = parseHeader(kronosHeaderFile)

    # If tickAudio doesn't exist, quit: it's not an audio obj
    if not tickAudio:
        print("ERROR: Kronos code does not contain an audio tick output.")
        return 1

    print("ins:", ins)
    print("outs:", outs)
    print("params:", params)
    print("buffers:", buffers)

    writeCpp(ins, outs, params, buffers)
    writeSC(ins, outs, params, buffers)

    return 0

if __name__ == '__main__':
    sys.exit(main())