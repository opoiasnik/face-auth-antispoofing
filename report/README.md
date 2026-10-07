# Správa (LaTeX)

Technický report semestrálneho zadania. Kompilácia: **pdfLaTeX + Biber**.

## Overleaf

Celá správa je **v jednom súbore `main.tex`** – vrátane bibliografie
(prostredie `filecontents*` na začiatku súboru vytvorí `references.bib` pri kompilácii).

1. Overleaf → *New Project* → *Blank Project* → obsah `main.tex` vložte do hlavného súboru.
2. *Menu* → Compiler: `pdfLaTeX`. Bibliografiu (biblatex, štýl `iso-numeric`)
   Overleaf spracuje cez Biber automaticky.
3. Grafy nahrajte do priečinka `figures/` v projekte Overleaf (pozri nižšie).
4. Ak používate oficiálnu šablónu z MS Teams, skopírujte do nej telo dokumentu,
   balíky, makrá `\todo` a `\optfigure` a prostredie `filecontents*`.

## Čo treba doplniť

Všetky miesta sú v PDF označené červeným **[TODO: …]**.

| Časť | Kto |
|---|---|
| Úvod, Analýza problematiky (teória, max. 3 strany), Záver, Abstrakt | **autori sami – AI je pri teórii zakázaná** |
| Tabuľky výsledkov (LFW, PAD, end-to-end) | čísla zo skriptov `backend/evaluation` |
| Interpretácie výsledkov, snímky obrazovky | autori |

## Grafy

Skopírujte PDF grafy z `backend/reports/` do `figures/` s týmito názvami:

| Zdroj | Cieľový súbor |
|---|---|
| `recognition-*/score_distribution.pdf` | `figures/score_distribution.pdf` |
| `recognition-*/det.pdf` | `figures/det.pdf` |
| `pad-*/score_distribution.pdf` | `figures/pad_score_distribution.pdf` |
| `pad-*/det.pdf` | `figures/pad_det.pdf` |
| `audit-*/rejection_reasons.pdf` | `figures/rejection_reasons.pdf` |

Kým graf chýba, v PDF je namiesto neho červený rámik.

## Zdroje

Bibliografia (prostredie `filecontents*` v `main.tex`) obsahuje 15 odborných zdrojov z rokov 2022–2025 overených cez DOI
(Crossref) alebo oficiálne stránky (ISO, ENISA, EUR-Lex), plus model SFace (2021)
a softvérové zdroje, ktoré sa do limitu 10 zdrojov nezapočítavajú.
