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


# Sentence filtration function

def filter_sentences(text: str) -> tuple[list[str], list[str]]:

    parts = re.split(SPLIT_REGEX, text)
    
    # Filter sentences that contain at least one keyword and are of a sensible length at minimum
    filtered = [p.strip() for p in parts if len(p.split()) >= 3 and any(w in p.strip().lower() for w in DICTIONARY_FILTER)]
    
    return parts, filtered