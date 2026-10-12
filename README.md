# Pràctica 1 MiV: Desmuntant la mentida visual
En aquesta pràctica s'evalua un plot poc adient trobat per Internet, que viola principis de Gestalt i Tufte de manera no intencionada, fent que el resultat final sigui un gràfic poc entenible.

## Plot original
![alt text](./plot-incorrecte.png)

Aquest plot presenta diversos problemes comentats a la documentació de la pràctica.

## Correccions
En aquest codi es troba tot el codi per adquisició, preprocessament i disposició de dades finals en un plot corregit. Els detalls dels preprocessaments, les decisions de disseny del nou plot i implementació de la interactivitat queden en la documentació de la pràctica.

## Set-up i Execució

El projecte està estructurat en dos directoris:
- **`data-fetching`**: Scripts per obtenir les dades oficials i d'enquestes sobre el Senat dels EUA.
- **`plotting`**: Preprocessament i visualització web interactiva.

### 1. Dependències de Python
Recomanem utilitzar un entorn virtual (per exemple amb `uv` o `venv`):
```bash
uv pip install -r plotting/requirements.txt
# o bé:
pip install -r plotting/requirements.txt
```

### 2. Generació de Dades per a la Visualització
Per preprocessar les dades de les enquestes i generar els actius estàtics:
```bash
python plotting/export_data.py
```
Aquestes dades ja queden incloses en el repositori.

### 3. Servidor Local
Per visualitzar el dashboard en local sense dependències externes no necessàries per la complexitat d'aquesta pràctica, utilitzem el servidor HTTP natiu de Python:
```bash
python3 -m http.server 8000 --directory plotting/web
```
Un cop iniciat, obre el navegador a:
**http://localhost:8000**