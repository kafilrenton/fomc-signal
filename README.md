# FOMC Signal Pipeline

### Research Question
Does the hawkish/dovish stance of FOMC communication carry information about Treasury yield moves beyond what markets had already priced in?

### Why?
Motivations for this project track back to my first-year macroeconomics module that I really enjoyed. I wanted to find an applied question in that area to work on while developing my programming skills, and the Federal Reserve's communications are a major driver of financial markets, which made them a good candidate for a data project.

The initial inspiration comes from the following paper when I was researching ideas: *"Trillion Dollar Words: A New Financial Dataset, Task & Market Analysis"* by Shah et al. (2023). Their work on hawkish/dovish classification provides a solid foundation to build upon.

## Current Pipeline & Looking Ahead

The pipeline scrapes FOMC documents from 2000 - 2026, splits the raw text into sentences, and isolates policy-relevant text using a keyword filter based on the Gorodnichenko et al. (2021) dictionary. These sentences are scored using the FOMC-RoBERTa model (Shah et al. 2023) on a Google Colab T4 GPU, and the probabilities are aggregated to document stance scores. Event-window market data is pulled from the San Francisco Fed and daily macro data from the FRED database.
The relevant code for all of these is located in the `src/` directory.

### Current Dataset Metrics
| Source                | Files   | Pre-filter Sentences | Post-filter Sentences |
| :-------------------- | :------ | :------------------- | :-------------------- |
| **Statements**        | 209     | 5,376                | 2,760                 |
| **Minutes**           | 208     | 161,125              | 98,888                |
| **Press Conferences** | 94      | 47,638               | 14,286                |
| **Total**             | **511** | **214,139**          | **115,934**           |


This dataset will be complemented by a statistical filter to smooth out stance scores, followed by an event-study to validate whether the signal predicts yield movements.


## References

1. Shah, A., Paturi, S., & Chava, S. (2023). *Trillion Dollar Words: A New Financial Dataset, Task & Market Analysis.* [arXiv](https://arxiv.org/abs/2305.07972) · [Model](https://huggingface.co/gtfintechlab/FOMC-RoBERTa) · [GitHub](https://github.com/gtfintechlab/fomc-hawkish-dovish)
2. Gorodnichenko, Y., Pham, T., & Talavera, O. (2021). *The Voice of Monetary Policy*. [NBER](https://www.nber.org/system/files/working_papers/w28592/w28592.pdf)
3. Federal Reserve Bank of San Francisco. [U.S. Monetary Policy Event-Study Database (USMPD)](https://www.frbsf.org/research-and-insights/data-and-indicators/us-monetary-policy-event-study-database/)
4. Federal Reserve Bank of St. Louis. [FRED](https://fred.stlouisfed.org/): series DFF, DGS2, DGS10.
5. Board of Governors of the Federal Reserve System. [FOMC calendars and historical materials](https://www.federalreserve.gov/monetarypolicy/fomc_historical_year.htm): source of all scraped statements, minutes and transcripts.

## License

The original code in this repository is licensed under the [MIT License](LICENSE).

**Third-Party Materials:**
The FOMC-RoBERTa model (Shah et al., 2023) is utilised in this project, which is distributed by the original authors under a CC BY-NC 4.0 license.
This project uses the model for research and educational purposes, in compliance with the non-commercial restriction. All credit for the model architecture and training data belongs to the original authors.