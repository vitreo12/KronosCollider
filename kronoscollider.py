# linux / macos: compile to ~/.cache
# windows: compile to C:\Windows\Temp

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
    paramsDict = {}

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
            bufsParams.append(bufName + "size")
            bufsParams.append(bufName + "frames")
            bufsParams.append(bufName + "numchans")
            bufsParams.append(bufName + "samplerate")

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
                paramsDict[paramName] = slotIndex
            else: # Add buffer params to existing buf dict
                for param in ["size", "frames", "numchans", "samplerate"]:
                    if param in paramName:
                        bufname = paramName.replace(param, "")
                        slotIndex = kronosHeaderFileSplit[i + 1]
                        slotIndex = slotIndex.replace("*KronosGetValue(instance, ", "")
                        slotIndexIdx = slotIndex.rfind(") = (void*)")
                        slotIndex = int(slotIndex[:slotIndexIdx])
                        bufsDict[bufname]["slotIndex_" + param] = slotIndex
    
    return (tickAudio, ins, outs, paramsDict, bufsDict)

def writeFiles(name, ins, outs, params, buffers):
    with open("KronosTemplate.cpp", "r") as text:
        cppFile = text.read()
    with open("KronosTemplate.sc", "r") as text:
        scFile = text.read()

    cppFile = cppFile.replace("KronosTemplate", name)
    scFile = scFile.replace("KronosTemplate", name)
    scArgs = "arg "
    scMultiNew = "^this.multiNew('audio',"
    scMultiOut = "init { arg ... theInputs;\n        inputs = theInputs;\n        ^this.initOutputs(" + str(outs) + ", rate);\n    }"
    
    # Block tick
    if len(params) + len(buffers) > 0:
        cppFile = cppFile.replace("// tick block", "KronosTickBlock(unit->m_obj, nullptr, 1);")

    # ins / outs
    if ins > 1:
        cppFile = cppFile.replace("// ins unit", "INS_UNIT")
        cppFile = cppFile.replace("// ins ctor", "INS_CTOR")
        cppFile = cppFile.replace("// ins dtor", "INS_DTOR")
        cppFile = cppFile.replace("// ins next", "INS_INTERLEAVE\n    KronosSetAudio(unit->m_obj, unit->m_ins);")
    else:
        cppFile = cppFile.replace("// ins next", "KronosSetAudio(unit->m_obj, IN(0));")

    for i in range(ins):
        inName = "in" + str(i + 1)
        scArgs = scArgs + inName + ","
        scMultiNew = scMultiNew + inName + ","
        scFile = scFile.replace("// rates", "// rates\n        if(" + inName + ".rate != audio, {\"" + name + ": expected '" + inName + "' to be at audio rate. Wrapping it in a K2A UGen.\".warn; " + inName + " = K2A.ar(" + inName + ")});")   
        
    if outs > 1:
        scFile = scFile.replace("// multiOut", scMultiOut)
        cppFile = cppFile.replace("// outs unit", "OUTS_UNIT")
        cppFile = cppFile.replace("// outs ctor", "OUTS_CTOR")
        cppFile = cppFile.replace("// outs dtor", "OUTS_DTOR")
        cppFile = cppFile.replace("// outs next", "KronosTickAudio(unit->m_obj, unit->m_outs, inNumSamples);\n    OUTS_DEINTERLEAVE")
    else:
        cppFile = cppFile.replace("// outs next", "KronosTickAudio(unit->m_obj, OUT(0), inNumSamples);")

    # params
    paramIdx = ins # start counting after audio inputs
    for paramName, slotIndex in params.items():
        cppFile = cppFile.replace("// params next", "// params next\n    PARAM_SET(" + str(slotIndex) + "," + str(paramIdx) + ")")
        scFile = scFile.replace("// rates", "// rates\n        if(" + paramName + ".rate == audio, {\"" + name + ": expected '" + paramName + "' to be at control rate. Wrapping it in a A2K UGen.\".warn; " + paramName + " = A2K.kr(" + paramName + ")});")
        scArgs = scArgs + paramName + ","
        scMultiNew = scMultiNew + paramName + ","
        paramIdx += 1

    # Buffers
    bufferIdx = paramIdx # start counting after params
    for bufName, params in buffers.items():
        scArgs = scArgs + bufName + ","
        scMultiNew = scMultiNew + bufName + ","
        scFile = scFile.replace("// rates", "// rates\n        if(" + bufName + ".class != Buffer, {\"" + name + ": expected '" + bufName + "' to be at control rate. Wrapping it in a A2K UGen.\".warn; " + bufName + " = A2K.kr(" + bufName + ")});")
        slotIndex = str(params["slotIndex"])
        slotIndexSize = str(params["slotIndex_size"])
        slotIndexFrames = str(params["slotIndex_frames"])
        slotIndexNumChans = str(params["slotIndex_numchans"])
        slotIndexSR = str(params["slotIndex_samplerate"])
        cppFile = cppFile.replace("// buffers unit", "// buffers unit\n    BUFFER_UNIT(" + bufName + ")")
        cppFile = cppFile.replace("// buffers ctor", "// buffers ctor\n    BUFFER_CTOR(" + bufName + ")")
        cppFile = cppFile.replace("// buffers next", "// buffers next\n    BUFFER_NEXT(" + bufName + "," + str(bufferIdx) + "," + slotIndex + "," + slotIndexSize + "," + slotIndexFrames + "," + slotIndexNumChans + "," + slotIndexSR + ")")
        cppFile = cppFile.replace("// buffers release", "// buffers release\n    BUFFER_RELEASE(" + bufName + ")")
        bufferIdx += 1

    if scArgs != "arg ":
        scArgs = scArgs[:-1] + ";"
        scMultiNew = scMultiNew[:-1] + ");"
        scFile = scFile.replace("// args", scArgs)
        scFile = scFile.replace("// multiNew", scMultiNew)

    print("CPP FILE \n")
    print(cppFile)
    
    print("SC FILE \n")
    print(scFile)
    
    with open("KronosTemplate.cpp", "w") as file:
        file.write(cppFile)
    with open("KronosTemplate.sc", "w") as file:
        file.write(scFile)

    os.rename("KronosTemplate.cpp", name + ".cpp")
    os.rename("KronosTemplate.sc", name + ".sc")

    return

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
    cppFile = cwd + "/KronosTemplate/KronosTemplate.cpp"
    cmakeFile = cwd + "/KronosTemplate/CMakeLists.txt"
    scFile = cwd + "/KronosTemplate/KronosTemplate.sc"
    shutil.copy(kronosFile, outDir)
    shutil.copy(cppFile, outDir)
    shutil.copy(cmakeFile, outDir)
    shutil.copy(scFile, outDir)
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

    #print("ins:", ins)
    #print("outs:", outs)
    #print("params:", params)
    #print("buffers:", buffers)

    writeFiles(name, ins, outs, params, buffers)

    # Rename files

    # Build

    # Copy folder to extensions dir

    return 0

if __name__ == '__main__':
    sys.exit(main())