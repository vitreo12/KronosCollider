#include "SC_PlugIn.h"
#include "KronosTemplate.h"

static InterfaceTable *ft;

// num params

#define INS_UNIT KronosaudioInputType* m_ins;
#define OUTS_UNIT KronosOutputType* m_outs;
#define BUFFER_UNIT(name) Buffer name;

#define INS_CTOR \
int insBufSize = sizeof(KronosaudioInputType) * BUFLENGTH; \
unit->m_ins = (KronosaudioInputType*)RTAlloc(unit->mWorld, insBufSize); \
if (!unit->m_ins) { \
    SETCALC(ClearUnitOutputs); \
    return; \
} \
memset(unit->m_ins, 0, insBufSize);

#define OUTS_CTOR \
int outsBufSize = sizeof(KronosOutputType) * BUFLENGTH; \
unit->m_outs = (KronosOutputType*)RTAlloc(unit->mWorld, outsBufSize); \
if (!unit->m_outs) { \
    SETCALC(ClearUnitOutputs); \
    return; \
} \
memset(unit->m_outs, 0, outsBufSize);

#define BUFFER_CTOR(name) \
unit->name.m_fbufnum = -1e9f; \
unit->name.m_failedBufNum = -1e9f;

#define INS_DTOR \
if (unit->m_ins) \
    RTFree(unit->mWorld, unit->m_ins);

#define OUTS_DTOR \
if (unit->m_outs) \
    RTFree(unit->mWorld, unit->m_outs); 

#define INS_INTERLEAVE \
for (int i = 0; i < unit->mNumInputs - NUM_PARAMS; i++) { \
    for (int y = 0; y < inNumSamples; y++) \
        unit->m_ins[y][i] = IN(i)[y]; \
}

#define OUTS_DEINTERLEAVE \
for (int i = 0; i < unit->mNumOutputs; i++) { \
    for (int y = 0; y < inNumSamples; y++) \
        OUT(i)[y] = unit->m_outs[y][i]; \
}

#define INS_MONO_NEXT KronosSetAudio(unit->m_obj, IN(0));
#define OUTS_MONO_NEXT KronosTickAudio(unit->m_obj, OUT(0), inNumSamples);
#define INS_MULTI_NEXT INS_INTERLEAVE KronosSetAudio(unit->m_obj, unit->m_ins);
#define OUTS_MULTI_NEXT KronosTickAudio(unit->m_obj, unit->m_outs, inNumSamples); OUTS_DEINTERLEAVE

#define BUFFER_CHECK_DATA(name) \
if (!bufData) { \
    if (unit->mWorld->mVerbosity > -1 && !unit->mDone && (unit->name.m_failedBufNum != fbufnum)) { \
        Print("KronosTemplate: '%s' contains no buffer data\n", #name); \
        unit->name.m_failedBufNum = fbufnum; \
    } \
    ClearUnitOutputs(unit, inNumSamples); \
    return; \
}

#define BUFFER_NEXT(name, input, slotIndex, slotIndexSize, slotIndexFrames, slotIndexNumChans, slotIndexSR) \
float fbufnum = ZIN0(input); \
if (fbufnum != unit->name.m_fbufnum) { \
    uint32 bufnum = (int)fbufnum; \
    World* world = unit->mWorld; \
    if (bufnum >= world->mNumSndBufs) \
        bufnum = 0; \
    unit->name.m_fbufnum = fbufnum; \
    unit->name.m_buf = world->mSndBufs + bufnum; \
} \
const SndBuf* buf = unit->name.m_buf; \
ACQUIRE_SNDBUF_SHARED(buf); \
const float* bufData = buf->data; \
BUFFER_CHECK_DATA(name); \
float bufSamples = (float)buf->samples; \
float bufFrames  = (float)buf->frames; \
float numChans   = (float)buf->channels; \
float bufSampleRate = buf->samplerate; \
*KronosGetValue(unit->m_obj, slotIndex) = (void*)bufData; \
*KronosGetValue(unit->m_obj, slotIndexSize) = (void*)&bufSamples; \
*KronosGetValue(unit->m_obj, slotIndexFrames) = (void*)&bufFrames; \
*KronosGetValue(unit->m_obj, slotIndexNumChans) = (void*)&numChans; \
*KronosGetValue(unit->m_obj, slotIndexSR) = (void*)&bufSampleRate;

#define BUFFER_RELEASE(name) \
RELEASE_SNDBUF_SHARED(unit->name.m_buf);

#define PARAM_SET(slotIndex, index) \
*KronosGetValue(unit->m_obj, slotIndex) = (void*)&IN0(index);

#define TICK_BLOCK KronosTickBlock(unit->m_obj, nullptr, 1);

struct Buffer {
    float m_fbufnum;
    float m_failedBufNum;
    SndBuf* m_buf;
};

struct KronosTemplate : Unit {
    KronosInstancePtr m_obj;
    float m_samplerate;
    // ins unit
    // outs unit
    // buffers unit
};

extern "C" {
void KronosTemplate_next_a(KronosTemplate* unit, int inNumSamples);
void KronosTemplate_Ctor(KronosTemplate* unit);
void KronosTemplate_Dtor(KronosTemplate* unit);
}

void KronosTemplate_Ctor(KronosTemplate* unit) {
    // ins ctor
    // outs ctor
    unit->m_obj = (KronosInstancePtr)RTAlloc(unit->mWorld, KronosGetSize());
    if (!unit->m_obj) {
        SETCALC(ClearUnitOutputs);
        return;
    }
    memset(unit->m_obj, 0, KronosGetSize());
    unit->m_samplerate = unit->mWorld->mSampleRate;
    KronosConfigure_RateAudio(&unit->m_samplerate);
    KronosInitialize(unit->m_obj, NULL);
    // buffers ctor
    SETCALC(KronosTemplate_next_a);
    KronosTemplate_next_a(unit, 1);
}

void KronosTemplate_Dtor(KronosTemplate* unit) {
    // ins dtor
    // outs dtor
    if (unit->m_obj)
        RTFree(unit->mWorld, unit->m_obj);
}

void KronosTemplate_next_a(KronosTemplate* unit, int inNumSamples) {
    // ins next
    // params next
    // buffers next
    // tick block
    // outs next
    // buffers release
}

PluginLoad(KronosTemplateUGens) 
{
    ft = inTable; 
    DefineDtorCantAliasUnit(KronosTemplate);
}
