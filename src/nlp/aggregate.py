from pathlib import Path
import pandas as pd

DATASETS = Path(__file__).resolve().parents[2] / "datasets"

def aggregate_scores():
    """Aggregate sentence probabilities into document stance scores."""

    df = pd.read_csv(DATASETS / "sentence_scores.csv")

    # Finding max argument label for each sentence
    df["argmax"] = df[["p_dovish", "p_hawkish", "p_neutral"]].idxmax(axis=1)

    # Identifying whether a sentence is of a certain stance and assign 1 or 0 for future counting
    df["ind_hawkish"] = (df["argmax"] == "p_hawkish").astype(int)
    df["ind_dovish"] = (df["argmax"] == "p_dovish").astype(int)

    grouped = df.groupby(["date", "source"])

    # Components for the hawkish measure of each file type
    total_sentences = grouped.size()
    count_hawkish = grouped["ind_hawkish"].sum()
    count_dovish = grouped["ind_dovish"].sum()

    out = pd.DataFrame({
        "stance_count": (count_hawkish - count_dovish) / total_sentences,
        "stance_prob": grouped["p_hawkish"].mean() - grouped["p_dovish"].mean()
    }).reset_index()

    out.to_csv(DATASETS / "meeting_scores.csv", index=False)
    print(f"Saved {len(out)} rows to meeting_scores.csv")

if __name__ == "__main__":
    aggregate_scores()