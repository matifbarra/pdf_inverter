# Checklist de deploy

## Antes de subir

- Verificá que la app arranca localmente con `streamlit run app.py`.
- Confirmá que `requirements.txt` tenga solo dependencias necesarias.
- Revisá que `app.py` sea el archivo principal.
- Revisá que `converter.py` tenga la lógica compartida.

## Subir a GitHub

```powershell
cd "c:\Users\matif\OneDrive\Documentos\curso github copilot\pdf_inverter"
git init
git add .
git commit -m "Initial web version of PDF Inverter"
git branch -M main
git remote add origin <URL_DE_TU_REPO>
git push -u origin main
```

## Deploy en Streamlit Cloud

1. Entrá en https://share.streamlit.io/
2. Conectá tu cuenta de GitHub.
3. Seleccioná el repositorio.
4. Indicá `app.py` como main file.
5. Hacé deploy.

## Si usás Render

- Build command: `pip install -r requirements.txt`
- Start command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`

## Después del deploy

- Probá subir un PDF chico primero.
- Verificá que la vista previa cargue bien.
- Confirmá que el botón de descarga genere el PDF final.