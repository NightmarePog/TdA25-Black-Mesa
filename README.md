# TDA25-BLACK-MESA

# How Does It Work?

Šablona pro vývoj aplikace pro Tour de App společně s vytvořením a nahráním výstupu.

## pipenv
- pipenv ( `pip install --user pipenv`)

## Flask
(`pip install Flask`)
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

## useful recources
[Tour De App](https://tourde.app/)
[task](https://tourde.app/zadani)
[Repository](https://github.com/NightmarePog/TdA25-Black-Mesa)