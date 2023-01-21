#include "SC_PlugIn.h"
#include "KronosTemplate.h"

static InterfaceTable *ft;

#define INTERLEAVE_INS \
for (int i = 0; i < unit->mNumInputs; i++) { \
    for (int y = 0; y < inNumSamples; y++) \
        unit->m_ins[y][i] = IN(i)[y]; \
}

#define DEINTERLEAVE_OUTS \
for (int i = 0; i < unit->mNumOutputs; i++) {
    for (int y = 0; y < inNumSamples; y++) \
        OUT(i)[y] = unit->m_outs[y][i]; \
}

#define CHECK_BUFFER_DATA(buffer) \
if (!bufData) { \
    if (unit->mWorld->mVerbosity > -1 && !unit->mDone && (buffer->m_failedBufNum != fbufnum)) { \
        Print("KronosTemplate: no buffer data\n"); \
        buffer->m_failedBufNum = fbufnum; \
    } \
    ClearUnitOutputs(unit, inNumSamples); \
    return; \
}

#define ACQUIRE_BUFFER(buffer, input) \
float fbufnum = ZIN0(input); \
if (fbufnum != buffer->m_fbufnum) { \
    uint32 bufnum = (int)fbufnum; \
    World* world = unit->mWorld; \
    if (bufnum >= world->mNumSndBufs) \
        bufnum = 0; \
    buffer->m_fbufnum = fbufnum; \
    buffer->m_buf = world->mSndBufs + bufnum; \
} \
const SndBuf* buf = unit->m_buf; \
ACQUIRE_SNDBUF_SHARED(buf); \
const float* bufData = buf->data; \
CHECK_BUFFER_DATA(buffer); \
float bufSamples = (float)buf->samples; \
float bufFrames  = (float)buf->frames; \
float bufSampleRate = buf->samplerate;

#define RELEASE_BUFFER(buffer) \
RELEASE_SNDBUF_SHARED(buffer->m_buf);

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
    unit->m_obj = (KronosInstancePtr)RTAlloc(unit->mWorld, KronosGetSize());
    if (!unit->m_obj) {
        SETCALC(ClearUnitOutputs);
        return;
    }
    memset(unit->m_obj, 0, KronosGetSize());
    unit->m_samplerate = unit->mWorld->mSampleRate;
    KronosConfigure_RateAudio(&unit->m_samplerate);

    // Mul ins ctor

    // Mul outs ctor

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
