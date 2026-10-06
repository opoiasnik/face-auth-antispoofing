# Používateľská príručka

## Požiadavky

* moderný prehliadač (Chrome, Edge, Firefox, Safari) s webkamerou,
* aplikácia otvorená cez **HTTPS** alebo `localhost` (inak prehliadač kameru nepovolí),
* rovnomerné osvetlenie tváre spredu, bez silného protisvetla.

## Registrácia

1. Otvorte **Registrácia** a zadajte používateľské meno (3–32 znakov: malé písmená,
   číslice, `.`, `_`, `-`) a voliteľne celé meno.
2. Povoľte prístup ku kamere.
3. Umiestnite tvár do oválu. Kým sa ovál nezmení na **zelený** a nezobrazí sa
   „Tvár je pripravená", postupujte podľa nápovedy (priblížte sa, zlepšite svetlo …).
4. Kliknite **Zaregistrovať tvár** a postupujte podľa pokynov v dolnej časti obrazu:
   * ● – pozerajte priamo do kamery,
   * ← / → – pomaly otočte hlavu doľava / doprava (cca 20–30°),
   * ↑ / ↓ – zdvihnite bradu / skloňte hlavu.

   Poradie pohybov je pri každom pokuse iné. Celé snímanie trvá približne 7 sekúnd.
5. Po úspešnom overení živosti sa vytvorí účet a ste automaticky prihlásení.

## Prihlásenie

* **Meno + tvár (1:1)** – zadáte meno a systém porovná tvár iba s vaším vzorom.
* **Iba tvár (1:N)** – systém vás vyhľadá medzi všetkými používateľmi.

Postup snímania je rovnaký ako pri registrácii. Po 5 neúspešných pokusoch počas
15 minút sa účet dočasne zablokuje.

## Hlásenia a riešenie problémov

| Hlásenie | Riešenie |
|---|---|
| Prístup ku kamere bol zamietnutý | povoľte kameru v nastaveniach stránky (ikona zámku v adresnom riadku) |
| Kamera vyžaduje zabezpečené pripojenie | otvorte aplikáciu cez `https://` alebo `http://localhost` |
| Tvár nie je v zábere / Priblížte sa | sadnite si bližšie, tvár do oválu |
| Príliš tma / Príliš svetla | otočte sa k zdroju svetla, nesedte proti oknu |
| Pohyby hlavy nezodpovedali výzve | otáčajte hlavou plynulejšie a výraznejšie, až keď sa zobrazí pokyn |
| Bol zistený pokus o podvrh | nepoužívajte fotografiu ani displej; pri falošnom poplachu zlepšite osvetlenie a skúste znova |
| Overenie zlyhalo – tvár sa nezhoduje | skúste lepšie svetlo; pri zmene vzhľadu (okuliare, brada) aktualizujte vzor v účte |
| Príliš veľa pokusov | počkajte 15 minút |

## Môj účet

* **História prihlásení** – všetky pokusy o prihlásenie do vášho účtu vrátane neúspešných
  (môžete tak odhaliť pokus o zneužitie).
* **Aktualizovať vzor tváre** – nové snímanie; uloží sa iba vtedy, ak sa nová tvár zhoduje
  s pôvodnou (zabraňuje prevzatiu účtu).
* **Odstrániť účet** – natrvalo vymaže účet aj biometrický vzor.

## Administrácia

Rolu administrátora pridelíte z príkazového riadku servera:

```bash
cd backend
python -m app.cli promote <pouzivatel>            # --revoke odoberie rolu
```

Administrátor vidí počty a úspešnosť operácií, dôvody zamietnutí, zoznam používateľov
(blokovanie, odstránenie) a kompletný audit log vrátane IP adries a skóre.

## Ochrana osobných údajov

* fotografie sa nikde neukladajú, spracujú sa iba v pamäti servera,
* ukladá sa 128-rozmerný vektor príznakov zašifrovaný kľúčom mimo databázy,
* používateľ môže svoje údaje kedykoľvek vymazať.
