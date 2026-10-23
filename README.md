# Growing wealth gap by reference-person education, 1989–2025

This project recreates the course example’s two-line comparison using the Federal Reserve’s Survey of Consumer Finances (SCF). **Education means the SCF reference person’s own education**, as stated in the example’s source note. The figure covers all SCF waves from 1989 through 2025 and uses constant 2025 dollars.

The chart is [`figure.png`](figure.png); its plotted estimates are in [`data/processed/means_by_reference_education.csv`](data/processed/means_by_reference_education.csv).

## Reproduce

Use Python 3 and install the packages in `requirements.txt`:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python get_data.py
python plot.py
```

`get_data.py` downloads the Federal Reserve’s Stata summary extract and codebook for every SCF wave from 1989 to 2025. The summary extracts supply all chart variables, so the larger full-data archives are not needed. Existing valid downloads are reused; use `python get_data.py --force` to download them again.

## Variable and groups

The Federal Reserve’s summary-variable program defines **`EDCL`**, education of the reference person, with the following categories in all waves:

| `EDCL` | SCF category | Figure series |
| ---: | --- | --- |
| 1 | No high-school diploma or GED | HS or less |
| 2 | High-school diploma or GED | HS or less |
| 3 | Some college or associate degree | Excluded |
| 4 | Bachelor’s degree or higher | BA or more |

The underlying education questions changed in 2016. In 1989–2013, the Fed derives its education grouping from schooling-years and degree responses; from 2016 onward, it uses the reference person’s highest-degree response (`X5931`). The Fed’s program maps both question formats to the same four `EDCL` categories, allowing this harmonized comparison across waves. The full codebooks for each year are retained under `data/documentation/`.

## Sample and calculation

- **Family sample:** keep families with a child living at home (`kids > 0` in the SCF summary extract). The Fed’s definition of `kids` counts natural, step-, and foster children of the reference person or spouse/partner.
- **Outcome:** mean family net worth (`networth`), calculated as a survey-weighted mean within each group and survey year.
- **Weights and implicates:** use the SCF family weight (`wgt`) to calculate the mean separately in each of the five implicates, then average the five implicate-specific means. The 1989 extract uses `X1` for its case/implicate identifier; later extracts use `Y1`. Their final digit identifies the implicate (1–5). The figure is a point-estimate comparison and does not display standard errors or confidence intervals.
- **Dollars:** the Federal Reserve’s summary-extract dollar variables are already inflation-adjusted to constant 2025 dollars; no additional deflator is applied.

## Comparing with the course example

The figure follows the example’s title, two group labels, family-with-child sample, mean-net-worth outcome, long-wave timeline, and line-chart layout. The endpoint labels and plotted values are calculated from the downloaded SCF files; no values were transcribed from the example image. The SCF summary-extract `kids` measure includes natural, step-, and foster children of the reference person **or spouse/partner**. If the example's note intends only the reference person's children, this is a slightly broader sample. Small visual differences may also remain due to font rendering and image dimensions.

## Data checks

- The `EDCL` categories (1–4) were confirmed across the 13 SCF summary extracts; the groups in the plot are based on the Federal Reserve's summary-variable program.
- The processed CSV contains an estimate for both plotted groups in each of the 13 survey waves (26 estimates total).
- As a consistency check against the course example, the SCF-derived 2025 means are $2,291,069 for “BA or more” and $269,180 for “HS or less.” Rounded to thousands, these match the example's endpoint labels ($2,291K and $269K). The example image was used only for comparison, not as a data source.

These checks confirm the category mapping, output coverage, and agreement with the example's labeled endpoints. I have not independently matched estimates to Federal Reserve published table values or calculated standard errors/confidence intervals.

## Survey years and retained files

The SCF waves used are **1989, 1992, 1995, 1998, 2001, 2004, 2007, 2010, 2013, 2016, 2019, 2022, and 2025**. For each wave, `data/raw/` contains `scfp_YEAR_stata.zip`, and `data/documentation/` contains `codebook_YEAR.txt`.

Official documentation: [SCF data and codebooks](https://www.federalreserve.gov/econres/scfindex.htm); [Federal Reserve summary-variable program](https://www.federalreserve.gov/econres/files/bulletin.macro.txt); [SCF recent changes](https://www.federalreserve.gov/econres/scf_recentchanges.htm).
