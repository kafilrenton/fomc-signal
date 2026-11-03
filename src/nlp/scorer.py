import os
import re
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
from transformers import pipeline

# Hugging Face access token
load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")

# Path to output folder
DATASETS = Path(__file__).resolve().parents[2] / "datasets"

# Regex on sentence boundaries (period, question, exclamation) 
# while avoiding common abbreviations like (U.S. or Mr.)
SPLIT_REGEX = r'(?<!U\.S\.)(?<!U\.K\.)(?<!Mr\.)(?<!Dr\.)(?<=[.!?])\s+(?=[A-Z"(])'

# Keyword filter based on Gorodnichenko et al. to keep relevant sentences
DICTIONARY_FILTER = {
    "inflation expectation", "interest rate", "bank rate", "fund rate", 
    "price", "economic activity", "inflation", "employment", "unemployment", 
    "growth", "exchange rate", "productivity", "deficit", "demand", "job market",
    "monetary policy", "anchor", "cut", "subdue", "decline", "decrease", "reduce",
    "low", "drop", "fall", "fell", "decelerate", "slow", "pause", "pausing", 
    "stable", "non-accelerating", "downward", "tighten", "ease", "easing", 
    "rise", "rising", "increase", "expand", "improve", "strong", "upward", 
    "raise", "high", "rapid"
}

# Regex pattern enforcing a word boundary at the start
# For example, allows "low" and its conjugates like "lowest", "lower" etc; but not "follow"
FILTER_PATTERN = re.compile(r'\b(' + '|'.join(DICTIONARY_FILTER) + r')', re.IGNORECASE)


# Sentence filtration function

def filter_sentences(text: str) -> tuple[list[str], list[str]]:

    parts = re.split(SPLIT_REGEX, text)
    
    # Filter sentences that contain at least one keyword and are of a sensible length at minimum
    filtered = [p.strip() for p in parts if len(p.split()) >= 3 and FILTER_PATTERN.search(p)]
    
    return parts, filtered


def main():

    sentences = []

    files = [
        ("statement.csv", "statement", "statement"),
        ("minutes.csv", "minutes", "minutes"),
        ("conference.csv", "conference_transcript", "conference")
    ]

    for filename, text_col, source_name in files:
        filepath = DATASETS / filename
        
        # Load CSV, dropping any rows where the main text is missing
        df = pd.read_csv(filepath, encoding="utf-8").dropna(subset=[text_col])
        
        # Stats to view unfiltered vs filtered sentence counts        
        unfiltered_count = 0
        filtered_count = 0

        for _, row in df.iterrows():
            
            unfiltered, filtered = filter_sentences(row[text_col])
            
            unfiltered_count += len(unfiltered)
            filtered_count += len(filtered)
            
            for i, sentence in enumerate(filtered):
                sentences.append({
                    "source": source_name, 
                    "date": row["date"], 
                    "sentence_id": i, 
                    "text": sentence
                })

        # Unfiltered vs filtered numbers for this file type
        print(f"\n[{source_name.upper()}]")
        print(f"Files: {len(df)}")
        print(f"Pre-filter sentences: {unfiltered_count:,}")
        print(f"Post-filter sentences: {filtered_count:,}")

    print(f"\nTotal sentences: {len(sentences):,}\n")

    classifier = pipeline('text-classification', model="gtfintechlab/FOMC-RoBERTa", token=HF_TOKEN, device=0, top_k=None)

   # Sort sentences by length before batching to speed up classification
    sentences.sort(key=lambda s: len(s["text"].split()))

    texts = [s["text"] for s in sentences]
    results = []
    chunk_size = 5000
    
    # Chunking to prevent Colab from hanging on tokenisation
    for i in range(0, len(texts), chunk_size):
        chunk = texts[i:i+chunk_size]
        print(f"Scoring chunk {i} to {min(i+chunk_size, len(texts))}...")
        
        # Result is a list of dictionaries like [{'label': 'LABEL_0', 'score': 0.1}, ...]
        chunk_results = classifier(chunk, batch_size=128, truncation=True)
        results.extend(chunk_results)

    # Attach model outputs back to the original sentence dictionaries
    for sentence, result in zip(sentences, results):
        
        probs = {r["label"]: r["score"] for r in result}
        
        sentence["p_dovish"] = probs["LABEL_0"]
        sentence["p_hawkish"] = probs["LABEL_1"]
        sentence["p_neutral"] = probs["LABEL_2"]

    # Convert list of dictionaries into DataFrame
    df_out = pd.DataFrame(sentences).sort_values(by=["date", "source", "sentence_id"])
    df_out.to_csv(DATASETS / "sentence_scores.csv", index=False)


if __name__ == "__main__":
    main()