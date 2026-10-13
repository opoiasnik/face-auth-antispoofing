# Správa (LaTeX)

Technický report semestrálneho zadania. Kompilácia: **pdfLaTeX** (bez Biberu – rýchle aj na bezplatnom pláne Overleaf).

## Overleaf

Celá správa je **v jednom súbore `main.tex`** – vrátane zoznamu literatúry
(prostredie `thebibliography` podľa STN ISO 690 na konci súboru).

1. Overleaf → *New Project* → *Blank Project* → obsah `main.tex` vložte do hlavného súboru.
2. *Menu* → Compiler: `pdfLaTeX`.
3. Grafy nahrajte do priečinka `figures/` v projekte Overleaf (pozri nižšie).
4. Ak používate oficiálnu šablónu z MS Teams, skopírujte do nej telo dokumentu,
   balíky, makrá `\todo` a `\optfigure` a prostredie `thebibliography`.

## Čo treba doplniť

Miesta sú v PDF označené červeným **[TODO: …]**:

* meno spolužiaka na titulnej strane,
* tabuľka testu so živými používateľmi (kap. 5.5) – vyžaduje skutočné pokusy pred
  kamerou; výsledky vypíše `python -m evaluation.audit_report`.

Ostatné výsledky (LFW, CASIA-FASD, útok statickým obrázkom, výkon) sú namerané
a grafy aj snímky obrazovky sú v priečinku `figures/`. V Overleaf nahrajte celý
priečinok `figures/` vedľa `main.tex`.

## Zdroje

Zoznam literatúry obsahuje 15 odborných zdrojov z rokov 2022–2025 overených cez DOI
(Crossref) alebo oficiálne stránky (ISO, ENISA, EUR-Lex). Navyše sú uvedené model
SFace (2021), použité databázy LFW (2007) a CASIA-FASD (2012) a softvérové zdroje –
tie sa do limitu 10 zdrojov nie starších ako 5 rokov nezapočítavajú.
