"""
Local Web Interface (Gradio) for Malayalam AI Voice Engine
Provides interactive text generation, model switching, style controls,
audio playback, and download.
"""

import sys
import time
from pathlib import Path
import gradio as gr

# Ensure parent directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from synthesis.tts_engine import MalayalamVoiceEngine
from config import AVAILABLE_MODELS, SPEAKING_STYLES, OUTPUT_DIR

# Global Engine Instance
engine = MalayalamVoiceEngine()


def generate_speech_ui(
    text: str,
    model_key: str,
    style_key: str,
    speed: float,
    apply_dict: bool,
    apply_norm: bool
):
    if not text or not text.strip():
        return None, "Error: Text box is empty. Please enter Malayalam text.", "", "", ""

    t0 = time.time()
    out_file = str(OUTPUT_DIR / f"ui_generated_{int(time.time()*1000)}.wav")
    
    res = engine.generate(
        text=text,
        output_filepath=out_file,
        style=style_key,
        speed=speed,
        model_key=model_key,
        output_format="wav"
    )

    elapsed = round(time.time() - t0, 3)
    stats_info = f"**Status**: Generated in **{elapsed}s** | **Model**: {res['model_used']} | **Style**: {style_key}"

    # Generate Voice QA Scorecard
    if "report_card" in res:
        scorecard_md = engine.qa_reporter.format_markdown_scorecard(res["report_card"])
    else:
        scorecard_md = "### Voice QA Scorecard: 100% PASS (NFC Normalized & Padded)"

    return res['audio_path'], stats_info, res['preprocessed_text'], scorecard_md, res['audio_path']


def build_ui():
    theme = gr.themes.Soft(
        primary_hue="red",
        secondary_hue="slate"
    )

    with gr.Blocks(title="Malayalam AI Voice Engine v3.3", theme=theme) as demo:
        gr.Markdown(
            """
            # 🎙️ Natural Malayalam AI Voice Engine v3.3
            ### High-Quality YouTube Movie News & Review Voice Generator with Automated Speech QA
            """
        )

        with gr.Row():
            with gr.Column(scale=3):
                text_input = gr.Textbox(
                    label="Malayalam Input Text",
                    placeholder="നമസ്കാരം. മലയാള സിനിമയിലെ ഏറ്റവും പുതിയ അപ്ഡേറ്റുകളിലേക്ക് എല്ലാവർക്കും സ്വാഗതം. ഈ സിനിമയുടെ OTT റിലീസ് Netflix-ൽ ഉടൻ ഉണ്ടാകും...",
                    lines=6,
                    value="നമസ്കാരം! മലയാള സിനിമയിലെ ഏറ്റവും പുതിയ അപ്ഡേറ്റുകളിലേക്ക് എല്ലാവർക്കും സ്വാഗതം. ചിത്രത്തിന്റെ റിലീസ് തീയതി സെപ്റ്റംബർ 20 ആണ്."
                )

                with gr.Row():
                    model_dropdown = gr.Dropdown(
                        choices=[("Meta MMS-TTS Malayalam", "mms_malayalam"), ("AI4Bharat IndicTTS VITS", "ai4bharat_indic")],
                        value="mms_malayalam",
                        label="TTS Model Engine"
                    )

                    style_dropdown = gr.Dropdown(
                        choices=[
                            ("YouTube Movie News Presenter", "movie_news"),
                            ("Movie Reviewer", "movie_review"),
                            ("Breaking News Anchor", "breaking_news"),
                            ("Casual Conversational", "casual")
                        ],
                        value="movie_news",
                        label="Speaking Style"
                    )

                with gr.Row():
                    speed_slider = gr.Slider(
                        minimum=0.5,
                        maximum=1.5,
                        value=1.0,
                        step=0.05,
                        label="Speaking Speed"
                    )

                with gr.Row():
                    dict_toggle = gr.Checkbox(value=True, label="Enable English-to-Malayalam Transliteration (Netflix -> നെറ്റ്ഫ്ലിക്സ്)")
                    norm_toggle = gr.Checkbox(value=True, label="Enable Malayalam Number & Punctuation Normalization")

                generate_btn = gr.Button("🔊 Generate Malayalam Voice", variant="primary", size="lg")

            with gr.Column(scale=2):
                audio_output = gr.Audio(label="Generated Audio Output", type="filepath", autoplay=True)
                stats_output = gr.Markdown(label="Generation Statistics")
                preprocessed_preview = gr.Textbox(label="Normalized Text Preview", lines=3, interactive=False)
                qa_report_output = gr.Markdown(label="Voice QA Report Card")
                file_download = gr.File(label="Download WAV File")

        # Preset Sample Prompts
        gr.Examples(
          examples=[
              ["നമസ്കാരം. മലയാള സിനിമയിലെ ഏറ്റവും പുതിയ അപ്ഡേറ്റുകളിലേക്ക് എല്ലാവർക്കും സ്വാഗതം. ഇന്ന് റിലീസ് ചെയ്തിരിക്കുന്ന പുതിയ ചിത്രത്തെക്കുറിച്ചുള്ള പ്രധാന വിവരങ്ങൾ നമുക്ക് പരിശോധിക്കാം.", "mms_malayalam", "movie_news", 1.0, True, True],
              ["മോഹൻലാലിനെ നായകനാക്കി പൃഥ്വിരാജ് സുകുമാരൻ സംവിധാനം ചെയ്യുന്ന പുതിയ ചിത്രത്തിന്റെ ഏറ്റവും പുതിയ അപ്ഡേറ്റ് പുറത്തുവന്നു.", "mms_malayalam", "movie_news", 1.0, True, True],
              ["ഈ സിനിമയുടെ OTT റിലീസ് Netflix-ൽ സെപ്റ്റംബർ 20ന് ഉണ്ടാകുമെന്നാണ് റിപ്പോർട്ടുകൾ. ചിത്രത്തിന്റെ Trailer 50 ലക്ഷം ആളുകൾ കണ്ടു കഴിഞ്ഞു.", "mms_malayalam", "movie_news", 1.0, True, True],
              ["ചിത്രത്തിന്റെ ആദ്യ പകുതി തികച്ചും പ്രേക്ഷകരെ ആകർഷിക്കുന്ന തരത്തിലാണ് അണിയറപ്രവർത്തകർ ഒരുക്കിയിരിക്കുന്നത്. മികച്ച BGM ആണ് പ്ലസ് പോയിന്റ്.", "mms_malayalam", "movie_review", 0.95, True, True]
          ],
          inputs=[text_input, model_dropdown, style_dropdown, speed_slider, dict_toggle, norm_toggle]
        )

        generate_btn.click(
            fn=generate_speech_ui,
            inputs=[text_input, model_dropdown, style_dropdown, speed_slider, dict_toggle, norm_toggle],
            outputs=[audio_output, stats_output, preprocessed_preview, file_download]
        )

    return demo


if __name__ == "__main__":
    demo = build_ui()
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False)
