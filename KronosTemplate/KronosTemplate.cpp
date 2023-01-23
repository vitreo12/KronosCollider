#include "SC_PlugIn.h"
#include "KronosTemplate.h"

static InterfaceTable *ft;

#define INS_UNIT KronosaudioInputType* m_ins;
#define OUTS_UNIT KronosOutputType* m_outs;
#define BUFFER_UNIT(name) Buffer name;

#define INS_INIT \
int insBufSize = sizeof(KronosaudioInputType) * BUFLENGTH; \
unit->m_ins = (KronosaudioInputType*)RTAlloc(unit->mWorld, insBufSize); \
if (!unit->m_ins) { \
    SETCALC(ClearUnitOutputs); \
    return; \
} \
memset(unit->m_ins, 0, insBufSize);

#define OUTS_INIT \
int outsBufSize = sizeof(KronosOutputType) * BUFLENGTH; \
unit->m_outs = (KronosOutputType*)RTAlloc(unit->mWorld, outsBufSize); \
if (!unit->m_outs) { \
    SETCALC(ClearUnitOutputs); \
    return; \
} \
memset(unit->m_outs, 0, outsBufSize);

#define BUFFER_INIT(name) \
unit->name->m_fbufnum = -1e9f; \
unit->name->m_failedBufNum = -1e9f;

#define INS_DTOR \
if (unit->m_ins) \
    RTFree(unit->mWorld, unit->m_ins);

#define OUTS_DTOR \ 
if (unit->m_outs) \
    RTFree(unit->mWorld, unit->m_outs); 

#define INS_INTERLEAVE \
for (int i = 0; i < unit->mNumInputs; i++) { \
    for (int y = 0; y < inNumSamples; y++) \
        unit->m_ins[y][i] = IN(i)[y]; \
}

#define OUTS_DEINTERLEAVE \
for (int i = 0; i < unit->mNumOutputs; i++) {
    for (int y = 0; y < inNumSamples; y++) \
        OUT(i)[y] = unit->m_outs[y][i]; \
}

#define BUFFER_CHECK_DATA(buffer) \
if (!bufData) { \
    if (unit->mWorld->mVerbosity > -1 && !unit->mDone && (buffer->m_failedBufNum != fbufnum)) { \
        Print("KronosTemplate: no buffer data\n"); \
        buffer->m_failedBufNum = fbufnum; \
    } \
    ClearUnitOutputs(unit, inNumSamples); \
    return; \
}

#define BUFFER_ACQUIRE(slotIndex, slotIndexSR, slotIndexSize, slotIndexFrames, slotIndexNumChans, buffer, input) \
float fbufnum = ZIN0(input); \
if (fbufnum != buffer->m_fbufnum) { \
    uint32 bufnum = (int)fbufnum; \
    World* world = unit->mWorld; \
    if (bufnum >= world->mNumSndBufs) \
        bufnum = 0; \
    buffer->m_fbufnum = fbufnum; \
    buffer->m_buf = world->mSndBufs + bufnum; \
} \
const SndBuf* buf = buffer->m_buf; \
ACQUIRE_SNDBUF_SHARED(buf); \
const float* bufData = buf->data; \
CHECK_BUFFER_DATA(buffer); \
float bufSamples = (float)buf->samples; \
float bufFrames  = (float)buf->frames; \
float numChans   = (float)buf->channels \
float bufSampleRate = buf->samplerate; \
*KronosGetValue(unit->m_obj, slotIndex) = (void*)bufData; \
*KronosGetValue(unit->m_obj, slotIndexSR) = (void*)bufSampleRate; \
*KronosGetValue(unit->m_obj, slotIndexSize) = (void*)bufSamples; \
*KronosGetValue(unit->m_obj, slotIndexFrames) = (void*)bufFrames; \
*KronosGetValue(unit->m_obj, slotIndexNumChans) = (void*)numChans;

#define BUFFER_RELEASE(buffer) \
RELEASE_SNDBUF_SHARED(buffer->m_buf);

#define PARAM_SET(slotIndex, value) \
*KronosGetValue(unit->m_obj, slotIndex) = (void*)value;

struct Buffer {
    float m_fbufnum;
    float m_failedBufNum;
    SndBuf* m_buf;
}

struct KronosTemplate : Unit {
    KronosInstancePtr m_obj;
    float m_samplerate;
    // Mul ins unit
    // Mul outs unit
    // Buffers unit
};

extern "C" {
void KronosTemplate_next_a(KronosTemplate* unit, int inNumSamples);
void KronosTemplate_Ctor(KronosTemplate* unit);
void KronosTemplate_Dtor(KronosTemplate* unit);
}

void KronosTemplate_Ctor(KronosTemplate* unit) {
    // Mul ins ctor
    // Mul outs ctor
    unit->m_obj = (KronosInstancePtr)RTAlloc(unit->mWorld, KronosGetSize());
    if (!unit->m_obj) {
        SETCALC(ClearUnitOutputs);
        return;
    }
    memset(unit->m_obj, 0, KronosGetSize());
    unit->m_samplerate = unit->mWorld->mSampleRate;
    KronosConfigure_RateAudio(&unit->m_samplerate);
    KronosInitialize(unit->m_obj, NULL);
    // Buffers ctor
    SETCALC(KronosTemplate_next_a);
    KronosTemplate_next_a(unit, 1);
}

void KronosTemplate_Dtor(KronosTemplate* unit) {
    // Mul ins dtor
    // Mul outs dtor
    if (unit->m_obj)
        RTFree(unit->mWorld, unit->m_obj);
}

void KronosTemplate_next_a(KronosTemplate* unit, int inNumSamples) {
    // Mul ins next
    // Params next
    // Buffers next (acquire, set)
    // Block tick
    // Audio tick
    // Mul outs next
    // Buffers release
}

PluginLoad(KronosTemplateUGens) 
{
    ft = inTable; 
    DefineDtorCantAliasUnit(KronosTemplate);
}
