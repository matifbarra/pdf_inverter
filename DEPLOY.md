# Deploy

This app is ready to deploy as a Streamlit web app.

## Recommended: Streamlit Community Cloud

1. Push this folder to a GitHub repository.
2. Open https://share.streamlit.io/
3. Choose the repository and branch.
4. Set the main file path to `app.py`.
5. Deploy.

Streamlit will install the packages from `requirements.txt` automatically.

## Alternative: Render

Use a Web Service with these values:

- Build command: `pip install -r requirements.txt`
- Start command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`

## Notes

- The app is web-first and does not require a desktop launcher.
- `converter.py` contains the shared PDF conversion logic.