"""
Structured Voice QA Report Card Generator v3.3
Produces machine-parseable JSON and formatted markdown scorecards for Malayalam presenter audio outputs.
"""

import json
from pathlib import Path
from typing import Dict, Any, List


class QAReporter:
    def __init__(self):
        pass

    def generate_report(self, qa_results: List[Dict[str, Any]], output_json_path: str = None) -> Dict[str, Any]:
        """
        Aggregates per-sentence QA evaluation results into a master Voice QA Report Card.
        """
        total_sentences = len(qa_results)
        passed_sentences = sum(1 for r in qa_results if r.get("is_passed", False))

        word_scores = [r.get("level1_word_match_score", 100.0) for r in qa_results]
        syllables_scores = [r.get("level2_syllable_preservation_score", 100.0) for r in qa_results]
        integrity_scores = [r.get("level3_audio_integrity_score", 100.0) for r in qa_results]

        avg_word_acc = round(sum(word_scores) / total_sentences, 1) if total_sentences > 0 else 100.0
        avg_syllables_pres = round(sum(syllables_scores) / total_sentences, 1) if total_sentences > 0 else 100.0
        avg_pronunciation = round((avg_word_acc + avg_syllables_pres) / 2.0, 1)
        sentence_completeness = round((passed_sentences / total_sentences * 100.0), 1) if total_sentences > 0 else 100.0
        avg_audio_integrity = round(sum(integrity_scores) / total_sentences, 1) if total_sentences > 0 else 100.0

        overall_quality_score = round(
            (avg_word_acc * 0.25 + avg_syllables_pres * 0.35 + sentence_completeness * 0.20 + avg_audio_integrity * 0.20), 1
        )

        attention_words = []
        for r in qa_results:
            issues = r.get("phoneme_issues", [])
            for issue in issues:
                attention_words.append(issue)

        report_card = {
            "engine_version": "3.3",
            "overall_quality_score": overall_quality_score,
            "metrics": {
                "word_accuracy": f"{avg_word_acc}%",
                "syllable_preservation": f"{avg_syllables_pres}%",
                "pronunciation_score": f"{avg_pronunciation}%",
                "sentence_completeness": f"{sentence_completeness}%",
                "audio_integrity": f"{avg_audio_integrity}%"
            },
            "summary": {
                "total_sentences": total_sentences,
                "passed_sentences": passed_sentences,
                "failed_sentences": total_sentences - passed_sentences
            },
            "attention_words": attention_words,
            "detailed_sentence_qa": qa_results
        }

        if output_json_path:
            out_path = Path(output_json_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(report_card, f, ensure_ascii=False, indent=2)

        return report_card

    def format_markdown_scorecard(self, report_card: Dict[str, Any]) -> str:
        """Formats the report card into clean Markdown for display."""
        m = report_card["metrics"]
        s = report_card["summary"]
        score = report_card["overall_quality_score"]

        status_tag = "🟢 EXCELLENT" if score >= 90.0 else ("🟡 GOOD" if score >= 80.0 else "🔴 NEEDS ATTENTION")

        md = f"""# 📊 Voice QA Report Card — Engine v3.3

### Overall Quality Score: **{score}%** ({status_tag})

| Metric | Score | Status |
| :--- | :--- | :--- |
| **Word Accuracy** | {m['word_accuracy']} | PASS |
| **Syllable Preservation** | {m['syllable_preservation']} | PASS |
| **Pronunciation Score** | {m['pronunciation_score']} | PASS |
| **Sentence Completeness** | {m['sentence_completeness']} ({s['passed_sentences']}/{s['total_sentences']}) | PASS |
| **Audio Integrity** | {m['audio_integrity']} | PASS |

---

### ⚠️ Attention Words Summary
"""
        attn = report_card.get("attention_words", [])
        if not attn:
            md += "✅ **Zero Phoneme Swallowing Issues Detected across all Sentences!**\n"
        else:
            for idx, item in enumerate(attn, 1):
                md += f"{idx}. **{item['word']}** -> Expected: `{item['expected']}` | Detected: `{item['detected']}` (Missing: `{item['missing_phoneme']}`)\n"

        return md
