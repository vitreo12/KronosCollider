#!/usr/bin/env python3

import argparse
import os
import platform
import shutil
import sys

def parseHeader(headerFile: str):
    with open(headerFile, "r") as text_file:
        kronosHeaderFile = text_file.read()
        
    ins = 0
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
            paramName = paramName[:kronosInstancePtrIdx]
            default = float(paramName[paramName.rfind("Default"):].replace("Default", "").replace("d", "."))
            paramName = paramName[:paramName.rfind("Default")].lower()
            if paramName not in bufsParams: # Exclude buffer params
                slotIndex = kronosHeaderFileSplit[i + 1]
                slotIndex = slotIndex.replace("*KronosGetValue(instance, ", "")
                slotIndexIdx = slotIndex.rfind(") = (void*)")
                slotIndex = int(slotIndex[:slotIndexIdx])
                paramsDict[paramName] = {}
                paramsDict[paramName]["slotIndex"] = slotIndex
                paramsDict[paramName]["default"] = default
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
    
    numParams = len(params) + len(buffers)
    cppFile = cppFile.replace("// num params", "#define NUM_PARAMS " + str(numParams))
    if numParams > 0:
        cppFile = cppFile.replace("// tick block", "TICK_BLOCK")

    # ins / outs
    if ins > 1:
        cppFile = cppFile.replace("// ins unit", "INS_UNIT")
        cppFile = cppFile.replace("// ins ctor", "INS_CTOR")
        cppFile = cppFile.replace("// ins dtor", "INS_DTOR")
        cppFile = cppFile.replace("// ins next", "INS_MULTI_NEXT")
    elif ins == 1: # ins can also be 0, in which case nothing needs to be added
        cppFile = cppFile.replace("// ins next", "INS_MONO_NEXT")

    for i in range(ins):
        inName = "in" + str(i + 1)
        scArgs = scArgs + inName + "=(0),"
        scMultiNew = scMultiNew + inName + ","
        scFile = scFile.replace("// rates", "// rates\n        if(" + inName + ".rate != 'audio', {\"" + name + ": expected '" + inName + "' to be at audio rate. Wrapping it in a K2A UGen.\".warn; " + inName + " = K2A.ar(" + inName + ")});")   
        
    if outs > 1:
        scFile = scFile.replace("UGen", "MultiOutUGen")
        scFile = scFile.replace("// multiOut", scMultiOut)
        cppFile = cppFile.replace("// outs unit", "OUTS_UNIT")
        cppFile = cppFile.replace("// outs ctor", "OUTS_CTOR")
        cppFile = cppFile.replace("// outs dtor", "OUTS_DTOR")
        cppFile = cppFile.replace("// outs next", "OUTS_MULTI_NEXT")
    else:
        cppFile = cppFile.replace("// outs next", "OUTS_MONO_NEXT")

    # params
    paramIdx = ins # start counting after audio inputs
    for paramName, param in params.items():
        slotIndex = param["slotIndex"]
        default = param["default"]
        cppFile = cppFile.replace("// params next", "// params next\n    PARAM_SET(" + str(slotIndex) + "," + str(paramIdx) + ")")
        # scFile = scFile.replace("// rates", "// rates\n        if(" + paramName + ".rate == audio, {\"" + name + ": expected '" + paramName + "' to be at control rate. Wrapping it in a A2K UGen.\".warn; " + paramName + " = A2K.kr(" + paramName + ")});")
        scArgs = scArgs + paramName + "=(" + str(default) + "),"
        scMultiNew = scMultiNew + paramName + ","
        paramIdx += 1

    # Buffers
    bufferIdx = paramIdx # start counting after params
    for bufName, param in buffers.items():
        scArgs = scArgs + bufName + "=(0),"
        scMultiNew = scMultiNew + bufName + ","
        # scFile = scFile.replace("// rates", "// rates\n        if(" + bufName + ".class != Buffer, {\"" + name + ": expected '" + bufName + "' to be at control rate. Wrapping it in a A2K UGen.\".warn; " + bufName + " = A2K.kr(" + bufName + ")});")
        slotIndex = str(param["slotIndex"])
        slotIndexSize = str(param["slotIndex_size"])
        slotIndexFrames = str(param["slotIndex_frames"])
        slotIndexNumChans = str(param["slotIndex_numchans"])
        slotIndexSR = str(param["slotIndex_samplerate"])
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

    #print("CPP FILE \n")
    #print(cppFile)
    
    #print("SC FILE \n")
    #print(scFile)
    
    with open("KronosTemplate.cpp", "w") as file:
        file.write(cppFile)
    with open("KronosTemplate.sc", "w") as file:
        file.write(scFile)

    os.rename("KronosTemplate.cpp", name + ".cpp")
    os.rename("KronosTemplate.sc", name + ".sc")

    return

def buildFiles(name, scPath, extPath):
    os.mkdir("build")
    os.chdir("build")
    windowsMingw = ""
    if platform.system() == "Windows":
        windowsMingw = "\"MinGW Makefiles\" -DCMAKE_MAKE_PROGRAM:PATH=\"make\""
    os.system("cmake " + windowsMingw + " -DSC_PATH=" + scPath + " -DKRONOS_TEMPLATE=" + name + " -DCMAKE_BUILD_TYPE=Release -DSUPERNOVA=ON ..")
    os.system("cmake --build . --config Release")
    os.mkdir(name)
    if platform.system() == "Linux":
        ext = '.so'
    else:
        ext = ".scx"
    shutil.copy(name + ext, name)
    shutil.copy(name + "_supernova" + ext, name)
    shutil.copy("../" + name + ".sc", name)
    dirInExtensions = extPath + "/" + name
    if os.path.exists(dirInExtensions):
        shutil.rmtree(dirInExtensions, ignore_errors=True)
    shutil.copytree(name, dirInExtensions)
    return

def getCache():
    if platform.system() == 'Windows':
        return "C:\\Windows\\Temp\\KronosCollider\\"
    else:
        return "~/.cache/KronosCollider/"
    
def main(kronosFile, scPath, extPath, removeCache) -> int:
    kronosFile = os.path.abspath(os.path.expanduser(kronosFile))
    if not os.path.exists(kronosFile):
        print("ERROR: " + kronosFile + " does not exist")
        return 1
    kronosFileSplit = os.path.splitext(kronosFile)
    name = kronosFileSplit[0].split('/')[-1]

    scPath = os.path.abspath(os.path.expanduser(scPath))
    extPath = os.path.abspath(os.path.expanduser(extPath))

    # mkdir in cache
    cacheKronosCollider = os.path.expanduser(getCache())
    if(not os.path.exists(cacheKronosCollider)):
        os.mkdir(cacheKronosCollider)
    outDir = cacheKronosCollider + name
    if os.path.exists(outDir):
        shutil.rmtree(outDir, ignore_errors=True)
    os.mkdir(outDir)

    # Copy files and cd into it
    cwd = os.path.dirname(os.path.realpath(__file__))
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
    if os.system(kc) != 0:
        return 1

    (tickAudio, ins, outs, params, buffers) = parseHeader(headerFile)

    # If tickAudio doesn't exist, quit: it's not an audio obj
    if not tickAudio:
        print("ERROR: Kronos code does not contain an audio tick output.")
        return 1

    #print("ins:", ins)
    #print("outs:", outs)
    #print("params:", params)
    #print("buffers:", buffers)
    
    writeFiles(name, ins, outs, params, buffers)
    buildFiles(name, scPath, extPath)

    # Remove the build folder (if)
    if removeCache:
        shutil.rmtree(outDir, ignore_errors=True)

    return 0

# Parse strings to boolean for a better CLI experience
def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

# Remove metavar from help file
#https://devpress.csdn.net/python/62fe2a1dc67703293080479b.html
class RemoveMetavarFormatter(argparse.HelpFormatter):
    def _format_action_invocation(self, action):
        if not action.option_strings:
            metavar, = self._metavar_formatter(action, action.dest)(1)
            return metavar
        else:
            parts = []
            if action.nargs == 0:
                parts.extend(action.option_strings)
            else:
                default = action.dest.upper()
                args_string = self._format_args(action, default)
                for option_string in action.option_strings:
                    parts.append('%s' % option_string)
                parts[-1] += ' %s'%args_string
            return ', '.join(parts)

if __name__ == '__main__':
    if platform.system() == 'Windows':
        extensionsDir = "~\\AppData\\Local\\SuperCollider\\Extensions"
    elif platform.system() == 'Darwin':
        extensionsDir = "~/Library/Application Support/SuperCollider/Extensions"
    else:
        extensionsDir = "~/.local/share/SuperCollider/Extensions/"
    
    scDir = "~/Sources/supercollider/"

    parser = argparse.ArgumentParser(
        prog = 'KronosCollider',
        description = 'Compile Kronos code to SuperCollider UGens',
        formatter_class = RemoveMetavarFormatter
    )
    parser.add_argument('file', metavar = 'file', type = str, help = 'The .k file to compile')
    parser.add_argument('-s','--scPath', metavar = '', dest = 'scPath', type = str, default = scDir,
                help = "The path to the SuperCollider source files. Defaults to: '" + scDir + "'")
    parser.add_argument('-e', '--extPath', metavar = '', dest = 'extPath', type = str, default = extensionsDir,
                help = "The path to the SuperCollider extensions directory. Defaults to: '" + extensionsDir + "'")
    parser.add_argument('-r', '--removeCache', metavar = '', dest = 'removeCache', type = str2bool, default = True,
                help = "Remove the build files from the cache folder in: '" + getCache() + "'")
    
    args = parser.parse_args()
    sys.exit(main(args.file, args.scPath, args.extPath, args.removeCache))
