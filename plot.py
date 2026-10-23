#!/usr/bin/env python3
"""Plot weighted SCF mean family net worth by reference-person education."""

from __future__ import annotations

import argparse
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
import pyreadstat
from PIL import Image, ImageDraw, ImageFont

YEARS = (1989, 1992, 1995, 1998, 2001, 2004, 2007, 2010, 2013, 2016, 2019, 2022, 2025)
GROUPS = ("BA or more", "HS or less")
COLORS = {"BA or more": (27, 27, 27), "HS or less": (153, 153, 153)}
WIDTH, HEIGHT = 1800, 1320
PLOT_LEFT, PLOT_RIGHT, PLOT_TOP, PLOT_BOTTOM = 288, 1548, 224, 1055
Y_MAX = 2_400_000


def read_summary_extract(archive: Path, destination: Path) -> pd.DataFrame:
    """Read the single official Stata summary extract in an archive."""
    with zipfile.ZipFile(archive) as zipped:
        candidates = [name for name in zipped.namelist() if name.lower().endswith(".dta")]
        if len(candidates) != 1:
            raise ValueError(f"Expected one .dta file in {archive}, found {candidates}")
        extracted = zipped.extract(candidates[0], destination)
    dataframe, _metadata = pyreadstat.read_dta(
        extracted, usecols=["y1", "x1", "edcl", "wgt", "kids", "networth"]
    )
    dataframe.columns = dataframe.columns.str.lower()
    return dataframe


def weighted_mean(frame: pd.DataFrame) -> float:
    usable = frame.dropna(subset=["networth", "wgt"])
    if usable.empty or usable["wgt"].sum() <= 0:
        raise ValueError("No weighted observations for a group in an implicate")
    return float((usable["networth"] * usable["wgt"]).sum() / usable["wgt"].sum())


def wave_estimates(year: int, raw_dir: Path) -> list[dict[str, int | float | str]]:
    with tempfile.TemporaryDirectory(prefix=f"scf-{year}-") as temp_dir:
        data = read_summary_extract(
            raw_dir / f"scfp_{year}_stata.zip", Path(temp_dir)
        )

    # The 1989 extract calls the case/implicate identifier X1; later waves use Y1.
    id_column = "y1" if "y1" in data.columns else "x1" if "x1" in data.columns else None
    if id_column is None:
        raise KeyError(f"{year} summary extract has neither Y1 nor X1 identifier")
    required = {"edcl", "wgt", "kids", "networth"}
    if missing := required - set(data.columns):
        raise KeyError(f"{year} summary extract is missing {sorted(missing)}")

    # The identifier's last digit identifies the SCF implicate, 1 through 5.
    data["implicate"] = data[id_column].astype("int64") % 10
    data = data[(data["kids"] > 0) & data["implicate"].between(1, 5)]
    data["group"] = None
    data.loc[data["edcl"] == 4, "group"] = "BA or more"
    data.loc[data["edcl"].isin([1, 2]), "group"] = "HS or less"

    results: list[dict[str, int | float | str]] = []
    for group in GROUPS:
        selected = data[data["group"] == group]
        per_implicate = [
            weighted_mean(selected[selected["implicate"] == implicate])
            for implicate in range(1, 6)
        ]
        results.append({
            "year": year,
            "group": group,
            "mean_networth_2025_usd": sum(per_implicate) / 5,
        })
    return results


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc"]
        if bold else
        ["/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc"]
    )
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def draw_figure(estimates: pd.DataFrame, output: Path) -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(image)
    title_font = load_font(44, bold=True)
    subtitle_font = load_font(38)
    axis_font = load_font(32)
    legend_font = load_font(34)
    note_font = load_font(25)
    value_font = load_font(29)
    small_font = load_font(26)

    draw.text((72, 27), "Growing wealth gap", font=title_font, fill="black")
    draw.text(
        (72, 88),
        "By education of SCF reference person, in constant (2025) dollars, 1989–2025",
        font=subtitle_font,
        fill="black",
    )

    x_step = (PLOT_RIGHT - PLOT_LEFT) / (len(YEARS) - 1)
    x_position = {year: PLOT_LEFT + index * x_step for index, year in enumerate(YEARS)}

    def y_position(amount: float) -> float:
        return PLOT_BOTTOM - (amount / Y_MAX) * (PLOT_BOTTOM - PLOT_TOP)

    # Match the example's clean horizontal grid and monetary y-axis.
    for tick in range(0, Y_MAX + 1, 400_000):
        y = y_position(tick)
        draw.line((PLOT_LEFT, y, PLOT_RIGHT, y), fill=(218, 218, 218), width=2)
        label = f"${tick:,.0f}"
        box = draw.textbbox((0, 0), label, font=axis_font)
        draw.text((PLOT_LEFT - 16 - (box[2] - box[0]), y - 20), label, font=axis_font, fill=(55, 55, 55))

    draw.line((PLOT_LEFT, PLOT_TOP, PLOT_LEFT, PLOT_BOTTOM), fill=(55, 55, 55), width=2)
    draw.line((PLOT_LEFT, PLOT_BOTTOM, PLOT_RIGHT, PLOT_BOTTOM), fill=(55, 55, 55), width=2)
    for year in YEARS:
        x = x_position[year]
        draw.line((x, PLOT_BOTTOM, x, PLOT_BOTTOM + 9), fill=(55, 55, 55), width=2)
        label = str(year)
        box = draw.textbbox((0, 0), label, font=axis_font)
        draw.text((x - (box[2] - box[0]) / 2, PLOT_BOTTOM + 17), label, font=axis_font, fill=(55, 55, 55))

    # Rotated vertical axis title.
    y_label = Image.new("RGBA", (470, 52), (255, 255, 255, 0))
    ImageDraw.Draw(y_label).text((0, 0), "Mean family net worth", font=legend_font, fill="black")
    y_label = y_label.rotate(90, expand=True)
    image.paste(y_label, (45, int((PLOT_TOP + PLOT_BOTTOM - y_label.height) / 2)), y_label)
    draw = ImageDraw.Draw(image)

    # The legend follows the example's inset box and line swatches.
    legend = (330, 258, 606, 380)
    draw.rectangle(legend, fill="white", outline=(190, 190, 190), width=3)
    for index, group in enumerate(GROUPS):
        y = 291 + index * 56
        draw.line((345, y + 15, 397, y + 15), fill=COLORS[group], width=7)
        draw.text((421, y - 8), group, font=legend_font, fill="black")

    for group in GROUPS:
        series = estimates[estimates["group"] == group].sort_values("year")
        points = [
            (x_position[int(row.year)], y_position(float(row.mean_networth_2025_usd)))
            for row in series.itertuples()
        ]
        draw.line(points, fill=COLORS[group], width=8, joint="curve")
        # Endpoint labels make the last-year comparison readable, as in the example.
        last = series.iloc[-1]
        endpoint = float(last["mean_networth_2025_usd"])
        label = f"${round(endpoint / 1000):,}K"
        draw.text((PLOT_RIGHT + 20, y_position(endpoint) - 23), label, font=value_font, fill=(55, 55, 55))

    draw.text((72, 1172), "Families with a child of the reference person or spouse/partner living at home.", font=note_font, fill=(90, 90, 90))
    draw.text((72, 1207), "Education is the SCF reference person's own education. Values use the Federal Reserve's summary extract,", font=note_font, fill=(90, 90, 90))
    draw.text((72, 1242), "with dollar amounts in constant 2025 dollars. Source: Survey of Consumer Finances, Federal Reserve Board.", font=note_font, fill=(90, 90, 90))

    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG", optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).parent / "data")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "figure.png")
    args = parser.parse_args()

    rows = [row for year in YEARS for row in wave_estimates(year, args.data_dir / "raw")]
    estimates = pd.DataFrame(rows)
    processed_dir = args.data_dir / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    csv_path = processed_dir / "means_by_reference_education.csv"
    estimates.to_csv(csv_path, index=False)
    draw_figure(estimates, args.output)
    print(estimates.to_string(index=False))
    print(f"\nSaved chart: {args.output}")
    print(f"Saved estimates: {csv_path}")


if __name__ == "__main__":
    main()
