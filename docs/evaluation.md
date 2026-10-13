# Testovanie a vyhodnotenie

Vyhodnotenie má tri úrovne: (1) automatické testy softvéru, (2) offline meranie
presnosti jednotlivých biometrických modulov podľa noriem, (3) end-to-end test
systému s reálnymi používateľmi a útokmi. Všetky skripty ukladajú výsledky do
`backend/reports/<typ>-<dátum>/` (JSON, CSV, Markdown tabuľka, grafy PNG + PDF).

## 1. Automatické testy

```bash
cd backend && pytest --cov=app        # 49 testov, pokrytie ~87 %
cd frontend && npm test               # jednotkové testy klienta
```

| Oblasť | Čo sa overuje |
|---|---|
| Póza hlavy | znamienko yaw/pitch, invariantnosť voči náklonu hlavy, degenerované body |
| Aktívna výzva | správny smer, nedostatočný pohyb, málo snímok s tvárou, náhodnosť poradia |
| Metriky | FAR/FRR, EER (aj analyticky pre dve Gaussovky), APCER/BPCER/ACER, monotónnosť ROC |
| Bezpečnosť | JWT (podpis, expirácia), šifrovanie vzorov, validácia produkčnej konfigurácie, rate-limit |
| Výzvy | jednorazovosť, expirácia, účel, serializácia |
| API end-to-end | registrácia → overenie, impostor, neznámy používateľ, útok fotografiou (pasívny aj aktívny), výmena tváre počas relácie, replay výzvy, chýbajúci krok, duplicitná tvár, 1:N, lockout, výmaz účtu (GDPR), práva admina, neplatný obrázok |

## 2. Rozpoznávanie tváre (ISO/IEC 19795-1)

```bash
python -m evaluation.evaluate_recognition --lfw
python -m evaluation.evaluate_recognition --dir data/faces   # vlastné fotky: data/faces/<osoba>/*.jpg
```

Protokol LFW *pairs* (6 000 párov: 3 000 genuine, 3 000 impostor). Výstupy:

* `table.md` – EER, FAR/FRR pri systémovom prahu 0,40, FRR pri FAR ≤ 1 % a ≤ 0,1 %,
* `score_distribution` – histogram skóre genuine vs. impostor,
* `far_frr` – FAR a FRR v závislosti od prahu,
* `roc`, `det` – ROC (log. os) a DET krivka.

Metriky:

* **FAR** (*False Acceptance Rate*) – podiel impostor porovnaní so skóre ≥ prah,
* **FRR** (*False Rejection Rate*) – podiel genuine porovnaní so skóre < prah,
* **EER** – bod, kde FAR = FRR (lineárna interpolácia),
* **FTA** (*Failure to Acquire*) – podiel obrázkov bez detegovanej tváre.

Výsledok (LFW, 6000 párov, FTA 0 %):

| Pracovný bod | Prah | FAR | FRR |
|---|---|---|---|
| EER | 0,266 | 2,47 % | 2,47 % |
| Systémový prah | 0,400 | 0,00 % | 3,90 % |
| FAR ≤ 1 % | 0,294 | 1,00 % | 2,63 % |
| FAR ≤ 0,1 % | 0,339 | 0,10 % | 3,03 % |

## 3. Detekcia prezentačných útokov (ISO/IEC 30107-3)

Dataset sa nahrá webkamerou (rôzne vzdialenosti, svetlo, uhly; ideálne viac osôb):

```bash
python -m evaluation.capture_dataset --out data/pad --label bona_fide     --count 200
python -m evaluation.capture_dataset --out data/pad --label attack/print  --count 200  # vytlačená fotka
python -m evaluation.capture_dataset --out data/pad --label attack/replay --count 200  # fotka/video na mobile
python -m evaluation.capture_dataset --out data/pad --label attack/screen --count 200  # monitor notebooku
python -m evaluation.evaluate_pad --dir data/pad
```

Rovnakú štruktúru (`bona_fide/`, `attack/<typ>/`, obrázky alebo videá) možno
použiť aj pre verejné datasety (CelebA-Spoof, Replay-Attack, OULU-NPU).

Metriky:

* **APCER** – podiel útokov daného typu klasifikovaných ako živá tvár; celkové APCER je
  maximum cez typy útokov (najhorší prípad),
* **BPCER** – podiel živých tvárí klasifikovaných ako útok,
* **ACER** = (APCER + BPCER) / 2,
* **BPCER20 / BPCER100** – BPCER pri APCER = 5 % / 1 %.

Výstupy: `table.md`, `score_distribution`, `apcer_bpcer`, `det` (krivka pre každý typ
útoku), `apcer_per_type`.

Výsledok na testovacej časti CASIA-FASD (2408 snímok: 591 živých, 712 ohnutá
fotografia, 536 fotografia s vystrihnutými očami, 569 replay):

| Prah | BPCER | APCER (max) |
|---|---|---|
| 0,20 | 5,58 % | 5,97 % |
| 0,50 (systémový) | 18,10 % | 1,68 % |
| 0,70 (pôvodný) | 34,35 % | 0,93 % |

EER 5,25 %, BPCER20 5,58 %. Pôvodný prah 0,70 zamietal príliš veľa živých tvárí,
preto bol znížený na 0,50. Snímky v tejto verzii databázy sú orezané okolo tváre,
takže výsledok je skôr pesimistický.

## 4. Aktívna výzva a celý systém

Aktívnu výzvu nemožno vyhodnotiť na statických datasetoch – testuje sa end-to-end
cez aplikáciu. Každý pokus sa zapisuje do auditného logu (režim, výsledok, dôvod
zamietnutia, skóre zhody a živosti, čas spracovania). Odporúčaný scenár:

| Scenár | Počet pokusov | Očakávaný výsledok |
|---|---|---|
| Registrovaný používateľ, 1:1 | 20 / osoba | úspech |
| Registrovaný používateľ, 1:N | 20 / osoba | úspech |
| Iná osoba s menom obete (impostor) | 20 | `no_match` |
| Vytlačená fotografia obete | 20 | `passive_spoof` alebo `active_challenge_failed` |
| Fotografia na mobile/monitore | 20 | `passive_spoof` alebo `active_challenge_failed` |
| Video obete s pohybmi hlavy | 20 | `active_challenge_failed` (iné poradie) / `passive_spoof` |
| Výmena osoby počas snímania | 10 | `identity_inconsistent` |
| Opakované odoslanie zachytenej požiadavky | 5 | `invalid_challenge` |

```bash
python -m evaluation.audit_report --since 2026-11-01
```

vytvorí tabuľku úspešnosti podľa režimu, priemerný a P95 čas a graf dôvodov zamietnutia.

Útok statickým obrázkom (umelo vygenerovaná tvár): 6/6 pokusov cez virtuálnu kameru
v prehliadači zamietla aktívna výzva (pasívne skóre 0,98), 30/30 pokusov priamo cez API
zamietla pasívna detekcia (priemerné skóre relácie 0,25).

## 5. Výkon

```bash
python -m evaluation.benchmark --image cesta/k/tvari.jpg --runs 200
```

Referenčné meranie (Intel Core i7-13650HX, ONNX Runtime CPU, snímka 640×360 px, 200 behov):

| Fáza | Priemer [ms] |
|---|---|
| Detekcia (YuNet) | 4,76 |
| Kvalita vzorky | 0,10 |
| Odhad pózy hlavy | 0,01 |
| Pasívna živosť (2× MiniFASNet) | 2,59 |
| Extrakcia príznakov (SFace) | 3,98 |
| Celý snímok | 12,23 |

Relácia s najviac 27 snímkami sa na serveri spracuje približne za 0,3 s; celkovú dobu
prihlásenia (~5–7 s) určuje hlavne čas potrebný na vykonanie pohybov.

## 6. Ladenie prahov

Prahy sa nastavujú v `.env` bez zmeny kódu. Postup:

1. Zo skriptu rozpoznávania zvoľte prah zhody pre požadované FAR (napr. FAR ≤ 0,1 %).
2. Zo skriptu PAD zvoľte prah živosti podľa požadovaného kompromisu APCER/BPCER
   (napr. bod BPCER20).
3. Prahy aktívnej výzvy (`YAW_THRESHOLD`, `PITCH_THRESHOLD`) upravte podľa auditného
   logu – pole `peak_delta` v odpovedi (pri `EXPOSE_SCORES=true`) ukazuje dosiahnutý pohyb.
