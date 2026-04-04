# PDF Inverter

Web app to convert dark PDF notes into a print-friendly PDF.

## Run locally

```powershell
cd "c:\Users\matif\OneDrive\Documentos\curso github copilot\pdf_inverter"
python -m pip install -r requirements.txt
streamlit run app.py
```

## What is included

- `app.py`: Streamlit UI.
- `converter.py`: PDF rendering and inversion logic.
- `requirements.txt`: Python dependencies.
- `DEPLOY.md`: deployment steps for Streamlit Cloud and Render.

## Notes

- The app is web-first and runs in the browser.
- The conversion logic is shared in one place to keep the project easier to maintain.

## Deploy

See [DEPLOY.md](DEPLOY.md) for the recommended deployment steps.