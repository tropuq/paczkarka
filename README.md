## Potrzebne programy
virtualenv, pandoc, pdflatex, convert, gcc, fpc i pewnie coś jeszcze

## Instalacja
```
virtualenv env
source env/bin/activate
pip install -r requirements.txt
python szkopul.py update
```
Na koniec należy wpisać dane do logowania i dodawania zadań w kodzie.

## Przykładowe użycie
### Typowe generowanie
```
python szkopul.py gen -n "nazwa zadania" -pgzr
python szkopul.py gen -n "nazwa zadania" -t "tag w przypadku dwuznacznosci" -pgzr
python szkopul.py gen -n "nazwa zadania" -i "index w przypadku dwuznacznosci" -pgzra
```

### Aktualizacja
aktualizuje listę w zadanka.txt:
```
python szkopul.py update
```

### Wyszukiwanie
wyszukuje wszystkie zadania które mają w nazwie frazę 'lol', a w tagach mają 'OI'
```
python szkopul.py search -n lol -t "OI"
```
