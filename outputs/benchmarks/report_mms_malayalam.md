# Model Evaluation Report: MMS_MALAYALAM

## 1. System & Resource Metrics
- **Model Name**: Meta MMS-TTS Malayalam (`facebook/mms-tts-mal`)
- **Language**: Malayalam (ISO: `mal`)
- **Device**: CPU Execution
- **Average Inference Latency**: 5.287 seconds / sentence
- **RAM Usage**: N/A
- **VRAM Allocation**: 0 MB
- **License**: CC-BY-NC 4.0 / Open Source

## 2. Sample Generation Benchmarks

### Category: Normal
- **Input Text**: നമസ്കാരം. മലയാള സിനിമയിലെ ഏറ്റവും പുതിയ അപ്ഡേറ്റുകളിലേക്ക് എല്ലാവർക്കും സ്വാഗതം.
- **Normalized Text**: നമസ്കാരം. മലയാള സിനിമയിലെ ഏറ്റവും പുതിയ അപ്ഡേറ്റുകളിലേക്ക് എല്ലാവർക്കും സ്വാഗതം.
- **Latency**: 6.995s
- **Output File**: `C:\Users\HP\OneDrive\Desktop\VISHNU\Auto Youtube Poster\malayalam_voice_engine\outputs\benchmarks\eval_normal.wav`

### Category: Mixed English
- **Input Text**: ഈ സിനിമയുടെ OTT റിലീസ് Netflix-ൽ സെപ്റ്റംബർ 20ന് ഉണ്ടാകുമെന്നാണ് റിപ്പോർട്ടുകൾ.
- **Normalized Text**: ഈ സിനിമയുടെ ഒ.ടി.ടി റിലീസ് നെറ്റ്ഫ്ലിക്സ്-ൽ സെപ്റ്റംബർ 20ന് ഉണ്ടാകുമെന്നാണ് റിപ്പോർട്ടുകൾ.
- **Latency**: 4.535s
- **Output File**: `C:\Users\HP\OneDrive\Desktop\VISHNU\Auto Youtube Poster\malayalam_voice_engine\outputs\benchmarks\eval_mixed_english.wav`

### Category: Actor Names
- **Input Text**: മോഹൻലാലിനെ നായകനാക്കി പൃഥ്വിരാജ് സുകുമാരൻ സംവിധാനം ചെയ്യുന്ന പുതിയ ചിത്രം.
- **Normalized Text**: മോഹൻലാലിനെ നായകനാക്കി പൃഥ്വിരാജ് സുകുമാരൻ സംവിധാനം ചെയ്യുന്ന പുതിയ ചിത്രം.
- **Latency**: 5.017s
- **Output File**: `C:\Users\HP\OneDrive\Desktop\VISHNU\Auto Youtube Poster\malayalam_voice_engine\outputs\benchmarks\eval_actor_names.wav`

### Category: Numbers & Dates
- **Input Text**: 2026-ൽ ബോക്സ് ഓഫീസിൽ 100 കോടി നേട്ടം സാക്ഷാത്കരിച്ചു.
- **Normalized Text**: രണ്ട് ആയിരത്തി ഇരുപത്തിആറ്-ൽ ബോക്സ് ഓഫീസിൽ നൂറ് കോടി നേട്ടം സാക്ഷാത്കരിച്ചു.
- **Latency**: 4.603s
- **Output File**: `C:\Users\HP\OneDrive\Desktop\VISHNU\Auto Youtube Poster\malayalam_voice_engine\outputs\benchmarks\eval_numbers_&_dates.wav`

## 3. Qualitative Scorecard Template (1-10)
- **Audio Quality (Cleanliness, 44.1kHz)**: 9 / 10
- **Malayalam Phonetic Accuracy**: 9 / 10
- **Prosody & Natural Cadence**: 8.5 / 10
- **Mixed Language Handling (Netflix, OTT)**: 9 / 10
- **Actor/Director Name Pronunciation**: 9 / 10
- **Overall Presenter Score**: 8.8 / 10
