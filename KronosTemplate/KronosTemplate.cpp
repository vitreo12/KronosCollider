#include "KronosTemplate.h"
#include "SC_PlugIn.h"

static InterfaceTable *ft;

// num params

#define CONFIG_AUDIO KronosConfigure_RateAudio(&unit->m_samplerate);

#define INS_UNIT KronosaudioInputType *m_ins;
#define OUTS_UNIT KronosOutputType *m_outs;
#define BUFFER_UNIT(name) Buffer name;

#define INS_CTOR                                                               \
  int insBufSize = sizeof(KronosaudioInputType) * BUFLENGTH;                   \
  unit->m_ins = (KronosaudioInputType *)RTAlloc(unit->mWorld, insBufSize);     \
  if (!unit->m_ins) {                                                          \
    SETCALC(ClearUnitOutputs);                                                 \
    return;                                                                    \
  }                                                                            \
  memset(unit->m_ins, 0, insBufSize);

#define OUTS_CTOR                                                              \
  int outsBufSize = sizeof(KronosOutputType) * BUFLENGTH;                      \
  unit->m_outs = (KronosOutputType *)RTAlloc(unit->mWorld, outsBufSize);       \
  if (!unit->m_outs) {                                                         \
    SETCALC(ClearUnitOutputs);                                                 \
    return;                                                                    \
  }                                                                            \
  memset(unit->m_outs, 0, outsBufSize);

#define BUFFER_CTOR(name)                                                      \
  unit->name.m_fbufnum = -1e9f;                                                \
  unit->name.m_failedBufNum = -1e9f;

#define INS_DTOR                                                               \
  if (unit->m_ins)                                                             \
    RTFree(unit->mWorld, unit->m_ins);

#define OUTS_DTOR                                                              \
  if (unit->m_outs)                                                            \
    RTFree(unit->mWorld, unit->m_outs);

#define INS_INTERLEAVE                                                         \
  auto numInputs = unit->mNumInputs - NUM_PARAMS;                              \
  auto sc_ins = unit->mInBuf;                                                  \
  auto k_ins = unit->m_ins;                                                    \
  for (int i = 0; i < numInputs; i++) {                                        \
    for (int y = 0; y < inNumSamples; y++)                                     \
      k_ins[y][i] = sc_ins[i][y];                                              \
  }

#define OUTS_DEINTERLEAVE                                                      \
  auto numOutputs = unit->mNumOutputs;                                         \
  auto sc_outs = unit->mOutBuf;                                                \
  auto k_outs = unit->m_outs;                                                  \
  for (int i = 0; i < numOutputs; i++) {                                       \
    for (int y = 0; y < inNumSamples; y++)                                     \
      sc_outs[i][y] = k_outs[y][i];                                            \
  }

#define INS_MONO_NEXT KronosSetAudio(unit->m_obj, IN(0));

#define OUTS_MONO_NEXT KronosTickAudio(unit->m_obj, OUT(0), inNumSamples);

#define INS_MULTI_NEXT INS_INTERLEAVE KronosSetAudio(unit->m_obj, unit->m_ins);

#define OUTS_MULTI_NEXT                                                        \
  KronosTickAudio(unit->m_obj, unit->m_outs, inNumSamples);                    \
  OUTS_DEINTERLEAVE

#define BUFFER_ACQUIRE_BUF(name, input)                                        \
  float fbufnum_##name = IN0(input);                                           \
  if (fbufnum_##name != unit->name.m_fbufnum) {                                \
    uint32 bufnum = (int)fbufnum_##name;                                       \
    World *world = unit->mWorld;                                               \
    if (bufnum >= world->mNumSndBufs)                                          \
      bufnum = 0;                                                              \
    unit->name.m_fbufnum = fbufnum_##name;                                     \
    unit->name.m_buf = world->mSndBufs + bufnum;                               \
  }                                                                            \
  const SndBuf *buf_##name = unit->name.m_buf;                                 \
  ACQUIRE_SNDBUF_SHARED(buf_##name);                                           \
  const float *bufData_##name = buf_##name->data;

#define BUFFER_PRINT_ERROR(name)                                               \
  if (unit->mWorld->mVerbosity > -1 && !unit->mDone &&                         \
      (unit->name.m_failedBufNum != fbufnum_##name)) {                         \
    Print("KronosTemplate: '%s' contains no buffer data\n", #name);            \
    unit->name.m_failedBufNum = fbufnum_##name;                                \
  }

#define BUFFER_CHECK_DATA_NEXT(name)                                           \
  if (!bufData_##name) {                                                       \
    BUFFER_PRINT_ERROR(name)                                                   \
    ClearUnitOutputs(unit, inNumSamples);                                      \
    return;                                                                    \
  }

#define BUFFER_CHECK_DATA_INIT(name)                                           \
  bool valid_##name = true;                                                    \
  if (!bufData_##name) {                                                       \
    BUFFER_PRINT_ERROR(name)                                                   \
    valid_##name = false;                                                      \
  }

#define BUFFER_SET_PARAMS(name, slotIndex, slotIndexSize, slotIndexFrames,     \
                          slotIndexNumChans, slotIndexSR)                      \
  float bufSamples_##name = (float)buf_##name->samples;                        \
  float bufFrames_##name = (float)buf_##name->frames;                          \
  float numChans_##name = (float)buf_##name->channels;                         \
  float bufSampleRate_##name = (float)buf_##name->samplerate;                  \
  *KronosGetValue(unit->m_obj, slotIndex) = (void *)bufData_##name;            \
  *KronosGetValue(unit->m_obj, slotIndexSize) = (void *)&bufSamples_##name;    \
  *KronosGetValue(unit->m_obj, slotIndexFrames) = (void *)&bufFrames_##name;   \
  *KronosGetValue(unit->m_obj, slotIndexNumChans) = (void *)&numChans_##name;  \
  *KronosGetValue(unit->m_obj, slotIndexSR) = (void *)&bufSampleRate_##name;

#define BUFFER_NEXT(name, input, slotIndex, slotIndexSize, slotIndexFrames,    \
                    slotIndexNumChans, slotIndexSR)                            \
  BUFFER_ACQUIRE_BUF(name, input)                                              \
  BUFFER_CHECK_DATA_NEXT(name);                                                \
  BUFFER_SET_PARAMS(name, slotIndex, slotIndexSize, slotIndexFrames,           \
                    slotIndexNumChans, slotIndexSR)

#define BUFFER_INIT(name, input, slotIndex, slotIndexSize, slotIndexFrames,    \
                    slotIndexNumChans, slotIndexSR)                            \
  BUFFER_ACQUIRE_BUF(name, input)                                              \
  BUFFER_CHECK_DATA_INIT(name);                                                \
  if (valid_##name) {                                                          \
    BUFFER_SET_PARAMS(name, slotIndex, slotIndexSize, slotIndexFrames,         \
                      slotIndexNumChans, slotIndexSR)                          \
  }

#define BUFFER_RELEASE_NEXT(name) RELEASE_SNDBUF_SHARED(unit->name.m_buf);

#define BUFFER_RELEASE_INIT(name)                                              \
  if (valid_##name) {                                                          \
    RELEASE_SNDBUF_SHARED(unit->name.m_buf);                                   \
  }

#define PARAM_SET(slotIndex, input)                                            \
  *KronosGetValue(unit->m_obj, slotIndex) = (void *)&IN0(input);

#define TICK_BLOCK KronosTickBlock(unit->m_obj, nullptr, 1);

struct Buffer {
  float m_fbufnum;
  float m_failedBufNum;
  SndBuf *m_buf;
};

struct KronosTemplate : Unit {
  KronosInstancePtr m_obj;
  float m_samplerate;
  // ins unit
  // outs unit
  // buffers unit
};

extern "C" {
void KronosTemplate_next_a(KronosTemplate *unit, int inNumSamples);
void KronosTemplate_Ctor(KronosTemplate *unit);
void KronosTemplate_Dtor(KronosTemplate *unit);
}

// This function makes sure that the first value of the parameters in sclang
// (including buffers) is used when initializing the kronos instance.
inline void KronosInit(KronosTemplate *unit) {
  // params next
  // buffers init
  KronosInitialize(unit->m_obj, NULL);
  // buffers release init
}

void KronosTemplate_Ctor(KronosTemplate *unit) {
  // ins ctor
  // outs ctor
  unit->m_obj = (KronosInstancePtr)RTAlloc(unit->mWorld, KronosGetSize());
  if (!unit->m_obj) {
    SETCALC(ClearUnitOutputs);
    return;
  }
  memset(unit->m_obj, 0, KronosGetSize());
  unit->m_samplerate = unit->mWorld->mSampleRate;
  // config audio
  // buffers ctor
  KronosInit(unit);
  SETCALC(KronosTemplate_next_a);
  KronosTemplate_next_a(unit, 1);
}

void KronosTemplate_Dtor(KronosTemplate *unit) {
  // ins dtor
  // outs dtor
  if (unit->m_obj)
    RTFree(unit->mWorld, unit->m_obj);
}

void KronosTemplate_next_a(KronosTemplate *unit, int inNumSamples) {
  // ins next
  // params next
  // buffers next
  // tick block
  // outs next
  // buffers release next
}

PluginLoad(KronosTemplateUGens) {
  ft = inTable;
  DefineDtorCantAliasUnit(KronosTemplate);
}
