"""
Enhanced Accessibility Features for Vision Chroma Pro
- AAA Compliance Suggestions
- Typography Audit
- Score Breakdown Analysis
"""

import json
from datetime import datetime

def suggest_aaa_compliant_colors(issues, pairs, colors):
    """Suggest color pairs that meet AAA (7:1) standard"""
    aaa_ready = []
    needs_work = []
    
    for pair in pairs:
        if pair['ratio'] >= 7.0:
            aaa_ready.append(pair)
        elif pair['ratio'] >= 4.5:
            needs_work.append({
                'current': pair,
                'suggestion': f"Lighten {pair['bg']} or darken {pair['fg']} for AAA"
            })
    
    return {
        'aaa_compliant': len(aaa_ready),
        'total_pairs': len(pairs),
        'percentage': round((len(aaa_ready) / len(pairs) * 100), 1) if pairs else 0,
        'needs_work': needs_work[:10]
    }

def analyze_typography_details(text, readability):
    """Detailed typography analysis"""
    word_count = len(text.split())
    sentence_count = max(1, len([s for s in text.split('.') if s.strip()]))
    avg_words_per_sentence = round(word_count / sentence_count, 1)
    
    flesch = readability.get('flesch_ease')
    
    recommendations = []
    if avg_words_per_sentence > 20:
        recommendations.append("Reduce average words per sentence (currently {})".format(avg_words_per_sentence))
    if flesch and flesch < 50:
        recommendations.append("Break up long paragraphs with subheadings")
    if flesch and flesch > 80:
        recommendations.append("Content is very simple - consider adding depth")
    
    return {
        'word_count': word_count,
        'sentence_count': sentence_count,
        'avg_words_per_sentence': avg_words_per_sentence,
        'recommendations': recommendations
    }

def compute_score_breakdown(num_issues, total_pairs, readability, text_length):
    """Break down what contributes to overall score"""
    breakdown = {
        'contrast': 100,
        'readability': 100,
        'content_quality': 100
    }
    
    # Contrast impact
    if total_pairs > 0:
        issue_percentage = (num_issues / total_pairs) * 100
        breakdown['contrast'] = max(0, 100 - (issue_percentage * 0.6))
    
    # Readability impact
    flesch = readability.get('flesch_ease')
    if flesch is not None:
        if flesch < 50:
            breakdown['readability'] = 60
        elif flesch < 65:
            breakdown['readability'] = 80
        else:
            breakdown['readability'] = 100
    
    # Content quality
    if text_length < 200:
        breakdown['content_quality'] = 50
    elif text_length < 1000:
        breakdown['content_quality'] = 75
    else:
        breakdown['content_quality'] = 100
    
    weighted_score = (
        breakdown['contrast'] * 0.5 +
        breakdown['readability'] * 0.3 +
        breakdown['content_quality'] * 0.2
    )
    
    return {
        'breakdown': breakdown,
        'weights': {'contrast': 50, 'readability': 30, 'content_quality': 20},
        'weighted_score': round(weighted_score, 1)
    }

def export_analysis_json(data):
    """Export full analysis as JSON for CI/CD integration"""
    export = {
        'metadata': {
            'url': data.get('url'),
            'timestamp': datetime.now().isoformat(),
            'version': '1.0'
        },
        'scores': {
            'overall': data.get('score'),
            'contrast_issues': len(data.get('issues', [])),
            'readability_flesch': data.get('readability', {}).get('flesch_ease'),
            'readability_grade': data.get('readability', {}).get('fk_grade')
        },
        'compliance': {
            'wcag_aa_issues': sum(1 for i in data.get('issues', []) if i['ratio'] < 4.5),
            'wcag_aaa_issues': sum(1 for i in data.get('issues', []) if i['ratio'] < 7.0)
        },
        'colors': {
            'palette': data.get('colors', [])[:12],
            'total_unique': len(data.get('colors', []))
        },
        'content': {
            'has_sufficient_text': len(data.get('text', '')) > 200 if 'text' in data else False
        }
    }
    return json.dumps(export, indent=2)