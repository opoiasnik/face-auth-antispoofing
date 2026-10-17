# Protokol skúšok s webkamerou

Autori: Oleh Poiasnik a Andrii Pervashov.

Protokol určuje postup merania úspešnosti autentifikácie a odolnosti proti
prezentačným útokom. Každý pokus sa zaznamenáva samostatne podľa scenára,
očakávaného rozhodnutia a skutočnej odpovede systému.

## Príprava

1. Spustite aplikáciu podľa README, povoľte kameru a použite rovnaké prahy počas celého merania.
2. Zapíšte dátum, commit, verzie modelov/SHA-256, prehliadač, kameru, osvetlenie a nastavenia prahov.
3. Použite pseudonymy `osoba_a` a `osoba_b`. Snímajte iba osoby, ktoré s tým súhlasia.
4. Zaregistrujte oboch autorov. Pri každom pokuse vytvorte novú výzvu.
5. Po každom pokuse doplňte jeden riadok do `report/results/manual-attempts.csv`.

## Scenáre

| Kód | Scenár | Odporúčaný počet | Očakávanie |
|---|---|---|---|
| genuine_verify | Registrovaná osoba, meno + tvár | 20 na osobu | prijatie |
| genuine_identify | Registrovaná osoba, bez mena | 20 na osobu | prijatie správnej osoby |
| impostor | Druhá osoba zadá meno prvej | 20 | zamietnutie |
| print | Vytlačená fotografia registrovanej osoby | 20 | zamietnutie |
| screen | Fotografia registrovanej osoby na displeji | 20 | zamietnutie |
| replay | Video registrovanej osoby s pohybmi hlavy | 20 | zamietnutie |
| identity_swap | Osoby sa vymenia počas jednej výzvy | 10 | zamietnutie |
| request_replay | Opakované odoslanie rovnakej požiadavky | 5 | neplatná výzva |

Počty pokusov predstavujú navrhnutý rozsah experimentu.
Zahrňte viac svetelných podmienok a vzdialeností. Nevyraďujte neúspešné pokusy
oprávnených osôb. Skúška útoku je úspešná pre obranu vtedy, keď systém útok zamietne.

## Záznam a výpočet

CSV stĺpce: `timestamp,scenario,participant,expected,actual,failure_reason,attempt_id,notes`.
`expected` a `actual` používajú `accept` alebo `reject`. Pri 1:N uveďte do poznámky,
či vrátená identita bola správna. `attempt_id` prepojí riadok so serverovým auditom,
ak server pokus zaznamenal. Chybu pred vytvorením auditného záznamu opíšte v poznámke.
Nesprávna identita sa počíta ako neúspešný pokus aj pri HTTP úspechu.

Pre každý scenár uveďte celkový počet N, počet správnych rozhodnutí K a 100 × K/N.
Pri N = 0 uvádzajte „nezmerané“, nie 0 % ani 100 %. Prevádzkový audit samotný
nepozná, či išlo o fotografiu, video alebo oprávneného človeka. Preto je ručné
označenie scenára potrebné. Neoznačené záznamy neklasifikujte podľa skóre.

Zo servera možno získať podporný prehľad:

```bash
cd backend
python -m evaluation.audit_report
```

Výsledky meraní sa zapíšu do tabuľky v časti „Test so živými používateľmi“
v `report/main.tex`. Po aktualizácii výsledkov sa report znovu skompiluje.
Surové fotografie a biometrické vzory sa neukladajú do verejného repozitára.
