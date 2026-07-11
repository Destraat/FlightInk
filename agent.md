# FlightInk Agent Instructions

## Rol

Je bent de software-agent voor FlightInk. Bouw en onderhoud een betrouwbare Python-applicatie die gratis ADS-B-data omzet naar een rustig 800×480 e-ink scherm voor vliegtuigen die over het ingestelde huispunt vliegen.

## Hoofddoel

Lever een werkende Raspberry Pi-app die:

1. gratis live vliegtuigposities ophaalt;
2. het relevantste toestel boven of vlak bij het huis selecteert;
3. vliegtuigtype, maatschappij, registratie, hoogte, snelheid, koers en afstand toont;
4. waar mogelijk gratis herkomst en bestemming bepaalt;
5. een groot correct zijaanzicht van het vliegtuig rendert;
6. actuele lokale weersomstandigheden vertaalt naar een eenvoudige e-ink achtergrond;
7. één vlag en één herkenbaar gebouw van de bestemming toont;
8. een PNG-preview kan maken zonder aangesloten hardware;
9. optioneel een Waveshare e-paper display kan aansturen.

## Niet-onderhandelbare eisen

- Gebruik geen betaalde API als verplichte dependency.
- De applicatie moet blijven werken wanneer route-, weer- of metadata ontbreekt.
- Geen API-sleutels, coördinaten of persoonsgegevens hardcoden.
- Alle externe verzoeken krijgen een timeout, duidelijke User-Agent en foutafhandeling.
- Het hoofdproces mag niet crashen door één mislukte API-call.
- Render eerst naar een Pillow-image; houd hardware-output als losse adapter.
- Houd rekening met ghosting: ververs een e-ink scherm niet onnodig vaak.
- Gebruik type hints, dataclasses en kleine testbare functies.
- Voeg tests toe bij iedere wijziging in selectie-, afstands-, mapping- of renderlogica.
- Voeg geen auteursrechtelijk onduidelijke vliegtuigfoto’s of logo’s toe.

## Gewenste architectuur

```text
flightink/
├── api/            # ADS-B, weer en optionele gratis routebronnen
├── domain/         # dataclasses, selectie en berekeningen
├── render/         # layout, vliegtuigvormen, weerachtergrond
├── display/        # PNG en Waveshare adapters
├── data/           # lokale mappings en cache
└── main.py         # orchestration en CLI
```

De eerste MVP mag in één `flightink.py` staan, maar splits deze zodra het bestand groter wordt dan ongeveer 500 regels.

## Vliegtuigweergave

- Toon het vliegtuig altijd als schoon zijaanzicht.
- Spiegel horizontaal op basis van koers, maar draai het toestel niet schuin.
- Gebruik een generieke vectorvorm per categorie als exact type ontbreekt:
  - narrow-body jet;
  - wide-body jet;
  - regional jet;
  - turboprop;
  - helicopter;
  - unknown.
- Gebruik maatschappij-aankleding alleen wanneer die betrouwbaar uit callsign/operator volgt.
- Speciale liveries mogen alleen via een registratie-specifieke lokale override worden toegepast.
- Voor zwart-wit e-ink moeten logo’s en kleurvlakken worden vertaald naar patronen, grijstinten of dither.

## Selectie van het relevante toestel

Bereken voor ieder toestel minimaal:

- horizontale afstand tot het huis met haversine;
- geldige airborne-status;
- naderend of wegvliegend op basis van vorige meting;
- geschatte tijd tot dichtste passage wanneer voldoende gegevens bestaan.

Voorkeursvolgorde:

1. toestel waarvan de voorspelde baan het huis het dichtst passeert;
2. daarna naderend toestel;
3. daarna kleinste horizontale afstand;
4. negeer grondvoertuigen en toestellen onder een configureerbare minimumhoogte.

## Routegegevens

Herkomst en bestemming zijn niet betrouwbaar aanwezig in ADS-B. Implementeer daarom trapsgewijs:

1. lokale cache op callsign + datum;
2. optionele gratis routebron;
3. afleiding alleen wanneer betrouwbaar;
4. anders expliciet `Route onbekend` tonen.

Nooit een route verzinnen op basis van alleen maatschappij of vliegrichting.

## Weer

Gebruik een gratis bron zonder verplichte betaalde sleutel, bijvoorbeeld Open-Meteo. Cache het resultaat minimaal tien minuten. Vertaal de huidige toestand naar eenvoudige achtergronden zoals helder, licht bewolkt, bewolkt, regen, mist of sneeuw. De wolken zijn decoratief en mogen het vliegtuig niet onleesbaar maken.

## Layout

Doelresolutie: 800×480.

- Linker/middenvlak: groot vliegtuig met veel witruimte.
- Rechterkolom: vlucht, route, hoogte, snelheid, koers en afstand.
- Rechtsonder: één bestemmingskaart met gebouw en één vlag.
- Onderrand: tijd, datum, weer en laatste update.
- Gebruik duidelijke typografische hiërarchie en hoge contrasten.
- Vermijd kleine tekst onder circa 14 px op 800×480.

## Uitvoering

Ondersteun minimaal:

```bash
python flightink.py --demo
python flightink.py --once
python flightink.py --loop
```

- `--demo`: volledig offline voorbeeld.
- `--once`: één live ophaling en PNG-render.
- `--loop`: periodiek verversen met fouttolerantie.

## Testen en acceptatie

Voer voor iedere pull request uit:

```bash
pytest
python flightink.py --demo
```

Acceptatiecriteria:

- Er wordt een geldige 800×480 PNG aangemaakt.
- Geen toestel resulteert in een nette wachtweergave.
- Ontbrekende typecode, callsign, registratie of hoogte veroorzaakt geen crash.
- Haversine-afstanden zijn getest.
- Horizontaal spiegelen volgt de koersregels.
- De vlag verschijnt maximaal één keer.
- Het bestemmingsgebouw staat niet in het hoofdvlak.

## Git-proces

- Werk op een featurebranch.
- Maak kleine, beschrijvende commits.
- Open een pull request naar `main`.
- Beschrijf in de PR: wat werkt, welke gratis bronnen zijn gebruikt, bekende beperkingen en hoe lokaal getest is.
- Merge niet automatisch wanneer tests ontbreken of hardwaregedrag niet aantoonbaar veilig is.
