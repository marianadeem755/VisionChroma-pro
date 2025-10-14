import textstat

def analyze_readability(text):
    if not text or len(text.strip())<80:
        return {"fk_grade": None, "summary": "Not enough text to analyze."}
    fk = textstat.flesch_kincaid_grade(text)
    fe = textstat.flesch_reading_ease(text)  # Added: Compute Flesch Reading Ease score
    summary = "Moderate"
    if fe < 50:  # Adjusted: Use Flesch Ease for summary (low = complex), keeping your thresholds similar
        summary = "Complex — simplify sentences and words."
    elif fe > 70:
        summary = "Easy — good for general audience."
    elif fk and fk > 10:  # Fallback to your original FK logic
        summary = "Complex — simplify sentences and words."
    elif fk and fk <= 6:
        summary = "Easy — good for general audience."
    return {
        "fk_grade": round(fk,2) if fk else None,
        "flesch_ease": round(fe,2) if fe else None,  # Added: Include for compatibility with typography analysis
        "summary": summary
    }