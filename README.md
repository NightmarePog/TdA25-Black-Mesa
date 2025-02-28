# ThinkTacToe
# Tvořeno ve spolupráci s Think Difrrent Academy
## Popis
naše hra ThinkTacToe je hra vytvořená ve spolupráci s Think Diffrent Academy za účelem popularizování hraní piškvorek
naše aplikace má nadčasové funkce jako Matchmaking, ELO a mnohem víc

### Guest účet
- Guest účet může hrát přátelské hry s ostatními hráči!
- **Omezení**: je to pouze dočasný uživatel a po odchodu ze stránky veškerá data jsou smažána

### Registrovaný uživatel
- registrovaný uživatel je uživatel který se k nám přihlásil a má například možností jako staty nebo Ranked hry
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
7. `/list`: list všech hráčů co jsou registrovaní


---

## Funkce

## Matchmaking
- **prostě klikni a hraj!**

## možná je někde schovaná kočička
- **Hernik approved**

### Multiplayer hra:
- **Vytvoření hry**: Hráč zadá obtížnost a název hry, poté je přesměrován na `/multiplayer-game/<uuid>`.
- **Připojení ke hře**: Hráč zadá kód hry a po ověření je přesměrován na `/multiplayer-game/<uuid>`.

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

# Děkujeme Tour De App a jeho týmu za možnost zůčastnit se této soutěže
