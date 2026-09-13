"""
Malayalam Movie Updates Presenter Voice Generator v2.0
Uses Presenter Markup Tags (<intro>, <headline>, <important>, <detail>, <transition>, <question>, <outro>)
and 5-stage Studio Audio Mastering Chain (-16 LUFS, -1 dBFS True-Peak Limiting).
"""

import sys
import os
import time
from pathlib import Path

# Force UTF-8 encoding on stdout for Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from synthesis.tts_engine import MalayalamVoiceEngine
from config import OUTPUT_DIR, DEFAULT_SAMPLE_RATE

# Full Presenter Marked-Up Script for the User's News Request
FULL_MARKUP_SCRIPT = """
<intro>
നമസ്കാരം! മലയാള സിനിമയിലെ ഏറ്റവും പുതിയ അപ്ഡേറ്റുകളിലേക്ക് എല്ലാവർക്കും സ്വാഗതം.
</intro>

<headline>
ഒന്നാമതായി... മോഹൻലാലിന്റെ 370-ാം ചിത്രം പ്രഖ്യാപിച്ചു! ജൂഡ് ആന്റണി ജോസഫും അഷിഖ് ഉസ്മാനും ഒന്നിക്കുന്നു!
</headline>

<important>
മോഹൻലാലും ജൂഡ് ആന്റണി ജോസഫും വീണ്ടും ഒന്നിക്കുന്ന പുതിയ ചിത്രത്തിന് വലിയ പ്രതീക്ഷകളാണ് ലഭിക്കുന്നത്.
</important>

<detail>
ചിത്രത്തിന്റെ നിർമ്മാണം അഷിഖ് ഉസ്മാൻ നിർവ്വഹിക്കുന്നു. മോഹൻലാലിന്റെ 370-ാമത്തെ ചിത്രമായാണ് ഇത് അറിയപ്പെടുന്നത്. ജൂഡ് ആന്റണി ജോസഫും മോഹൻലാലും ഒന്നിക്കുന്ന രണ്ടാമത്തെ ചിത്രമാണിത്. ചിത്രത്തിന്റെ കൂടുതൽ വിവരങ്ങൾ ഉടൻ പുറത്തുവരുമെന്നാണ് റിപ്പോർട്ടുകൾ.
</detail>

<transition>
ഇനി അടുത്ത പ്രധാന വാർത്തയിലേക്ക് വരാം.
</transition>

<headline>
രണ്ടാമതായി... സംവൃത സുനിൽ തിരിച്ചെത്തുന്നു! ദിലീഷ് പോത്തനും അൽഫോൺസ് പുത്രനും ഒപ്പം പുതിയ ചിത്രം!
</headline>

<important>
നീണ്ട ഇടവേളയ്ക്ക് ശേഷം സംവൃത സുനിൽ മലയാള സിനിമയിലേക്ക് തിരിച്ചെത്തുകയാണ്.
</important>

<detail>
ഷാഹിദ് അറഫാത്ത് സംവിധാനം ചെയ്യുന്ന പുതിയ ചിത്രത്തിലാണ് സംവൃത സുനിൽ പ്രധാന വേഷത്തിലെത്തുന്നത്. ദിലീഷ് പോത്തനും ചിത്രത്തിലുണ്ട്. അൽഫോൺസ് പുത്രനും ചിത്രത്തിന്റെ ഭാഗമാകുന്നു. ചിത്രത്തിന്റെ ഷൂട്ടിംഗ് ആരംഭിച്ചു കഴിഞ്ഞു.
</detail>

<transition>
ഇനി മൂന്നാമത്തെ പ്രധാന അപ്ഡേറ്റ്.
</transition>

<headline>
മൂന്നാമതായി... മമ്മൂട്ടിയുടെ കിടിലൻ പുതിയ ലുക്ക്! മേള ഫസ്റ്റ് ലുക്ക് പുറത്ത്!
</headline>

<important>
മമ്മൂട്ടിയുടെ 75-ാം ജന്മദിനത്തോടനുബന്ധിച്ച് പുതിയ ചിത്രമായ മേളയുടെ ടൈറ്റിലും ഫസ്റ്റ് ലുക്കും പുറത്തിറങ്ങി.
</important>

<detail>
സംവിധാനം നിതീഷ് സഹദേവ്. തിരക്കഥ നിതീഷ് സഹദേവ്, അനുരാജ് ഒ.ബി. നിർമ്മാണം മമ്മൂട്ടി കമ്പനി. ഛായാഗ്രഹണം ജിംഷി ഖാലിദ്. നിലവിൽ കാരൈക്കുടിയിലാണ് ചിത്രീകരണം നടക്കുന്നത്. ഫസ്റ്റ് ലുക്കിലെ മമ്മൂട്ടിയുടെ പുതിയ ലുക്കിന് മികച്ച പ്രതികരണമാണ് ലഭിക്കുന്നത്.
</detail>

<transition>
ഇനി അടുത്ത തരംഗമായ വാർത്തയിലേക്ക്.
</transition>

<headline>
നാലാമതായി... ആശ ട്രെയിലർ പുറത്ത്! ഉർവശിയും ജോജു ജോർജും നേർക്കുനേർ!
</headline>

<important>
ഉർവശി, ഐശ്വര്യ ലക്ഷ്മി, ജോജു ജോർജ്, വിജയരാഘവൻ എന്നിവർ പ്രധാന വേഷത്തിലെത്തുന്ന ആശ ചിത്രത്തിന്റെ ട്രെയിലർ പുറത്തിറങ്ങി.
</important>

<detail>
സംവിധാനം സഫർ സനൽ. മിസ്റ്ററി ത്രില്ലർ വിഭാഗത്തിൽപ്പെടുന്ന ചിത്രം സെപ്റ്റംബർ 11ന് തിയേറ്ററുകളിൽ എത്തും. റോഡ് അപകടത്തെ തുടർന്നുണ്ടാകുന്ന നിയമപോരാട്ടമാണ് ട്രെയിലറിൽ പ്രധാനമായും കാണിക്കുന്നത്.
</detail>

<transition>
ഇനി അഞ്ചാമത്തെ സിനിമ വാർത്ത.
</transition>

<headline>
അഞ്ചാമതായി... റോഷൻ മാത്യു + ദിവ്യ പ്രഭ! ഡോൺ പാലത്തറയുടെ പുതിയ ചിത്രം പ്രഖ്യാപിച്ചു!
</headline>

<important>
സംവിധായകൻ ഡോൺ പാലത്തറയുടെ പുതിയ ചിത്രം ഏകദേശം ദി അൺസെർട്ടന്റി പ്രിൻസിപ്പിൾ പ്രഖ്യാപിച്ചു.
</important>

<detail>
ചിത്രത്തിൽ റോഷൻ മാത്യു, ദിവ്യ പ്രഭ, ജിതിൻ പുത്തഞ്ചേരി, വിനയ് ഫോർട്ട്, അർഷ ബൈജു, മഹേഷ് നാരായണൻ, ശാന്തി ബാലചന്ദ്രൻ എന്നിവർ അണിനിരക്കുന്നു. കൊച്ചിയുടെ പശ്ചാത്തലത്തിൽ സിനിമാരംഗത്ത് കരിയർ കെട്ടിപ്പടുക്കാൻ ശ്രമിക്കുന്ന യുവാക്കളുടെ ജീവിതമാണ് പ്രമേയം.
</detail>

<transition>
ഇനി ആറാമത്തെ മാസ് അപ്ഡേറ്റ്.
</transition>

<headline>
ആറാമതായി... ഐ ആം ഗെയിം ട്രെയിലർ പുറത്ത്! ദുൽഖർ സൽമാന്റെ മാസ് തിരിച്ചുവരവ്!
</headline>

<important>
ദുൽഖർ സൽമാൻ നായകനായ ഐ ആം ഗെയിം സെപ്റ്റംബർ 3ന് തിയേറ്ററുകളിലെത്തി.
</important>

<detail>
സംവിധാനം നഹാസ് ഹിദായത്ത്. ക്രൈം ആക്ഷൻ ത്രില്ലർ വിഭാഗത്തിൽപ്പെടുന്ന ചിത്രം അഞ്ച് ഭാഷകളിലാണ് റിലീസ് ചെയ്തത്. ചിത്രത്തിന്റെ റിലീസിന് മുന്നോടിയായി അഡ്വാൻസ് ബുക്കിംഗിലും മികച്ച പ്രതികരണമാണ് ലഭിച്ചത്.
</detail>

<transition>
ഇനി ഉടൻ റിലീസാകുന്ന മലയാള സിനിമകളുടെ കലണ്ടർ പരിശോധിക്കാം.
</transition>

<detail>
സെപ്റ്റംബർ 10ന് രന്താൾ. സെപ്റ്റംബർ 11ന് ആശ, പ്രഥമ ദൃഷ്ട്യാ കുറ്റക്കാർ, അമാനുഷികം, ഡോണ്ട് ട്രബിൾ ദി ട്രബിൾ, മണ്ടാടി എന്നിവ തിയേറ്ററുകളിലെത്തും. സെപ്റ്റംബർ 18ന് ബൊളഗോലം, വരാഹം, നിംറോഡ്, വൺ പ്രിൻസസ് സ്ട്രീറ്റ്, ക്രെഡിറ്റ് സ്കോർ, അവരൻ എന്നിവ റിലീസ് ചെയ്യും.
</detail>

<transition>
ഇനി ഒ.ടി.ടി വാർത്തയിലേക്ക് വരാം.
</transition>

<headline>
തുടക്കം ഒ.ടി.ടിയിലേക്ക്!
</headline>

<important>
മോഹൻലാലിന്റെ മകൾ വിസ്മയ മോഹൻലാൽ പ്രധാന വേഷത്തിലെത്തിയ തുടക്കം ഉടൻ ഒ.ടി.ടിയിൽ എത്തും.
</important>

<detail>
റിപ്പോർട്ടുകൾ പ്രകാരം സെപ്റ്റംബർ 18ന് ജിയോ ഹോട്ട്സ്റ്റാറിൽ ചിത്രം സ്ട്രീമിംഗ് ആരംഭിക്കും.
</detail>

<transition>
ഇനി മറ്റ് പ്രധാന സിനിമാ വാർത്തകൾ ഒറ്റനോട്ടത്തിൽ.
</transition>

<detail>
മോഹൻലാലിന്റെ അതി മനോഹരം ചിത്രീകരണം പൂർത്തിയാക്കി. ഡബ്ബിംഗ് ജോലികൾ പുരോഗമിക്കുകയാണ്. ഡിസംബർ 24, 2026 ആണ് റിലീസ് തീയതി. പാതിരാക്കുറുക്കൻ ചിത്രത്തിലൂടെ ജഗദീഷ്, മുകേഷ്, സിദ്ദിഖ്, അശോകൻ എന്നിവർ 16 വർഷത്തിന് ശേഷം വീണ്ടും ഒന്നിക്കുന്നു. മമ്മൂട്ടി – ധനുഷ് ചിത്രം ഓം ചാപ്റ്റർ വൺ പുതിയ ലുക്ക് പുറത്തുവന്നു. പ്രഥമ ദൃഷ്ട്യാ കുറ്റക്കാർ സെപ്റ്റംബർ 11ന് തിയേറ്ററുകളിലെത്തും.
</detail>

<outro>
കൂടുതൽ സിനിമ വിശേഷങ്ങൾക്കായി ചാനൽ സബ്സ്ക്രൈബ് ചെയ്യൂ. അടുത്ത വാർത്തകളുമായി വീണ്ടും കാണാം, നന്ദി!
</outro>
"""


def generate_markup_presentation(model_key: str = "xtts_v2"):
    print("=" * 70)
    print(f"[*] Generating Presenter Presentation v3.3 using model '{model_key}' (Automated Speech QA System)")
    print("=" * 70)
    sys.stdout.flush()

    engine = MalayalamVoiceEngine(default_model_key=model_key)

    output_filename = f"Malayalam_Movie_News_Presenter_{model_key}_v3.3.wav"
    output_path = str(OUTPUT_DIR / output_filename)

    res = engine.generate_from_markup(
        markup_text=FULL_MARKUP_SCRIPT,
        output_filepath=output_path,
        output_format="wav"
    )

    duration_sec = round(len(res["waveform"]) / DEFAULT_SAMPLE_RATE, 2)
    scorecard = engine.qa_reporter.format_markdown_scorecard(res["report_card"])

    print("\n" + "=" * 70)
    print(f"[🎉 SUCCESS] Presenter Presentation v3.3 Created Successfully!")
    print(f"    📁 Audio File Path    : {res['audio_path']}")
    print(f"    📊 Metadata JSON Path  : {res['metadata_path']}")
    print(f"    📋 Voice QA Report Path: {res['qa_report_path']}")
    print(f"    ⭐ Overall Quality Score: {res['report_card']['overall_quality_score']}%")
    print(f"    ⏱️ Audio Duration     : {duration_sec} seconds (~{round(duration_sec/60, 2)} minutes)")
    print(f"    🚀 Total Processing    : {res['generation_time']} seconds")
    print(f"    📊 Segments Count     : {res['segments_count']}")
    print("=" * 70)
    print("\n" + scorecard)

    return res['audio_path']


if __name__ == "__main__":
    import sys
    model_choice = "xtts_v2"
    if len(sys.argv) > 1:
        model_choice = sys.argv[1]
    generate_markup_presentation(model_key=model_choice)

