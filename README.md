# TDA25-BLACK-MESA

## Popis
Tato webová aplikace umožňuje uživatelům hrát piškvorky:
- **Lokálně**: Hráči mohou hrát na jednom zařízení.
- **Multiplayer**: Hráči mohou hrát mezi sebou přes internet.
- Každý tah se ukládá do uživatelského účtu.
- Uložené hry lze později zobrazit nebo dohrát (nedohrané hry). Dohrané hry již nelze znovu rozehrát.

### Guest účet
- Guest uživatel má stejné funkce jako registrovaný uživatel.
- **Omezení**: Pokud zavře všechny stránky webové aplikace a do 15 sekund se nevrátí, jeho účet bude automaticky smazán, až znovu vejde na webovou stránku.

### Registrovaný uživatel
- Registrovaný uživatel má trvalý účet, který není smazán (pokud nevymaže local storage).
- Přihlášení je trvalé, dokud se uživatel ručně neodhlásí.

---

## Technologie
- **Backend**: Flask
- **Frontend**: HTML, CSS, JavaScript
- **Ukládání dat**:
  - Veškerá důležitá data se ukládají do databáze.
  - Frontend ukládá nezbytná data do local storage (např. `userId`).

---

## Struktura stránek

### Přehled stránek:
1. `/login`: Uživatel se může přihlásit nebo registrovat jako guest.
2. `/register`: Registrace nového uživatele.
3. `/menu`: Hlavní stránka, kde uživatel vidí:
   - Uložené hry.
   - Možnost vytvořit novou multiplayer nebo lokální hru.
   - Připojení k existující multiplayer hře pomocí kódu.
4. `/game`: Stránka pro lokální hru (na jednom zařízení).
5. `/game/<uuid>`: Zobrazení nebo dohrání uložené hry.
6. `/multiplayer-game/<uuid>`: Multiplayer hra nebo sledování průběhu, pokud už jsou 2 hrající hráči.

### Pravidla přesměrování:
- Nepřihlášený uživatel je automaticky přesměrován na `/login`.
- Po přihlášení je uživatel přesměrován na `/menu`.

---

## Funkce

### Lokální hra:
- Hráč zadá obtížnost a jména Player 1 a Player 2.
- Po kliknutí na tlačítko je přesměrován na `/game`.

### Multiplayer hra:
- **Vytvoření hry**: Hráč zadá obtížnost a název hry, poté je přesměrován na `/multiplayer-game/<uuid>`.
- **Připojení ke hře**: Hráč zadá kód hry a po ověření je přesměrován na `/multiplayer-game/<uuid>`.

### Uložené hry:
- Hráč může:
  - **Dohrát** hru kliknutím na tlačítko "Play" (pokud hra není dohraná).
  - **Zobrazit** průběh kliknutím na "Show".
  - **Smazat** hru kliknutím na "Delete".
- U dohraných her tlačítko "Play" není dostupné a nahrazuje jej text "Game already played".

## Team: Black Mesa
- **Zeno**: Full-stack developer
- **Nightmare**: Back-end developer
- **Maferix**: Front-end developer
- **Blahaj(plushie)**: mental support

## pipenv
- pipenv ( `pip install --user pipenv`)

## pip
(`pip install pipenv flask flask-sqlalchemy requests flask_socketio`)
launch: venv\Scripts\activate

## How to run application?

```
flask --app app/app.py init-db
flask --app app/app.py run
```
or just run
Linux: start.sh
Windows: start.bat

local application address: `http://127.0.0.1:5000`

### Docker

```
docker build . -t tda-flask
docker run -p 8080:80 -v ${PWD}:/app tda-flask
```

local application address: `http://127.0.0.1:8080`

## useful resources
[Tour De App](https://tourde.app/)
[task](https://tourde.app/zadani)
[Repository](https://github.com/NightmarePog/TdA25-Black-Mesa)

