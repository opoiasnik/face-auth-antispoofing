# REST API

Základná cesta: `/api/v1`. Interaktívna dokumentácia (mimo produkcie): `/docs`.
Autorizované volania posielajú hlavičku `Authorization: Bearer <JWT>`.

## Endpointy

| Metóda | Cesta | Autorizácia | Popis |
|---|---|---|---|
| GET | `/health/live` | – | proces beží |
| GET | `/health/ready` | – | databáza a modely pripravené (503 inak) |
| POST | `/challenges` | – | vydá jednorazovú výzvu `{purpose: "enroll" \| "authenticate"}` |
| POST | `/biometrics/quality` | – | rýchla kontrola kvality jednej snímky (navádzanie) |
| POST | `/enrollment` | – | registrácia: používateľ + vzor tváre, vráti JWT |
| POST | `/auth/verify` | – | overenie 1:1 (meno + tvár), vráti JWT |
| POST | `/auth/identify` | – | identifikácia 1:N (iba tvár), vráti JWT |
| GET | `/users/me` | používateľ | profil |
| GET | `/users/me/attempts` | používateľ | história vlastných pokusov |
| PUT | `/users/me/face` | používateľ | výmena vzoru (nová relácia musí zodpovedať starému vzoru) |
| DELETE | `/users/me` | používateľ | výmaz účtu aj vzoru (GDPR čl. 17) |
| GET | `/admin/users` | admin | zoznam používateľov |
| PATCH | `/admin/users/{id}/active?active=false` | admin | blokovanie účtu |
| DELETE | `/admin/users/{id}` | admin | odstránenie používateľa |
| GET | `/admin/attempts` | admin | audit log |
| GET | `/admin/stats` | admin | agregované štatistiky |

## Príklad toku

```http
POST /api/v1/challenges
{"purpose": "authenticate"}

201 Created
{
  "challenge_id": "kq3...Zx",
  "purpose": "authenticate",
  "actions": ["center", "look_up", "turn_right"],
  "expires_in": 90,
  "capture": {"frames_per_step": 5, "step_duration_ms": 2200, "lead_in_ms": 700}
}
```

```http
POST /api/v1/auth/verify
{
  "username": "alice",
  "challenge_id": "kq3...Zx",
  "frames": [
    {"step": 0, "image": "<base64 JPEG>"},
    ...
    {"step": 2, "image": "<base64 JPEG>"}
  ]
}

200 OK
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {"id": 1, "username": "alice", "full_name": "Alice", "is_admin": false, ...},
  "match_score": 0.7412,
  "liveness": {
    "passive_liveness": 0.9634,
    "active_liveness": {"passed": true, "steps": [...]},
    "consistency": 0.6120,
    "quality_issues": {}
  }
}
```

`match_score` a `liveness` sa vracajú iba pri `FA_SECURITY__EXPOSE_SCORES=true`
(vývoj, ladenie prahov). V produkcii sú skryté, aby útočník nemohol iteratívne
optimalizovať vstup podľa skóre (*hill-climbing*).

## Formát chýb

```json
{"error": {"code": "biometric_rejected", "message": "Liveness challenge was not completed",
           "details": {"reason": "active_challenge_failed", "quality_issues": {}}}}
```

| HTTP | `code` | `details.reason` | Význam |
|---|---|---|---|
| 400 | `invalid_challenge` | – | výzva neexistuje, vypršala, bola použitá alebo chýbajú snímky kroku |
| 401 | `biometric_rejected` | `quality` | žiadna použiteľná frontálna snímka |
| 401 | `biometric_rejected` | `passive_spoof` | pasívna detekcia odhalila podvrh |
| 401 | `biometric_rejected` | `active_challenge_failed` | pohyby nezodpovedajú výzve |
| 401 | `biometric_rejected` | `identity_inconsistent` | osoba sa počas relácie zmenila |
| 401 | `biometric_rejected` | `no_match` | tvár sa nezhoduje / neznámy používateľ |
| 401 | `unauthorized` | – | chýbajúci, neplatný alebo expirovaný JWT |
| 403 | `forbidden` | – | chýba rola admin |
| 409 | `conflict` | `duplicate_face` / – | tvár alebo meno už existuje |
| 413 | `payload_too_large` | – | príliš veľká požiadavka / snímka |
| 422 | `validation_error`, `invalid_image` | – | neplatný vstup |
| 429 | `too_many_requests` | – | rate-limit alebo dočasné zablokovanie účtu |
| 503 | `service_unavailable` | – | modely nie sú načítané |
