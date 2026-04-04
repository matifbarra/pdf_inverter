from __future__ import annotations

import streamlit as st

from converter import DEFAULT_SETTINGS, preview_first_page, process_pdf_bytes, suggested_output_name


APP_STYLE = """
<style>
    :root {
        color-scheme: dark;
    }

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(34, 197, 94, 0.18), transparent 28%),
            radial-gradient(circle at top right, rgba(59, 130, 246, 0.18), transparent 24%),
            linear-gradient(180deg, #0b1220 0%, #0f172a 42%, #111827 100%);
        color: #e5eefc;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(15, 23, 42, 0.96), rgba(2, 6, 23, 0.98));
        border-right: 1px solid rgba(148, 163, 184, 0.18);
    }

    .hero {
        padding: 1.8rem 1.9rem;
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 28px;
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.92), rgba(30, 41, 59, 0.78));
        box-shadow: 0 24px 70px rgba(15, 23, 42, 0.45);
        margin-bottom: 1.25rem;
    }

    .eyebrow {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.38rem 0.8rem;
        border-radius: 999px;
        background: rgba(34, 197, 94, 0.12);
        border: 1px solid rgba(34, 197, 94, 0.25);
        color: #b8f3cb;
        font-size: 0.82rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin-bottom: 1rem;
    }

    .hero h1 {
        margin: 0;
        font-size: 2.5rem;
        line-height: 1.02;
        letter-spacing: -0.04em;
    }

    .hero p {
        margin: 0.95rem 0 0;
        max-width: 64ch;
        color: #c8d2e8;
        font-size: 1.02rem;
        line-height: 1.6;
    }

    .pill-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.65rem;
        margin-top: 1.2rem;
    }

    .pill {
        padding: 0.55rem 0.8rem;
        border-radius: 999px;
        background: rgba(15, 23, 42, 0.72);
        border: 1px solid rgba(148, 163, 184, 0.18);
        color: #e2e8f0;
        font-size: 0.88rem;
    }

    .surface {
        padding: 1.15rem 1.15rem 0.95rem;
        border-radius: 24px;
        border: 1px solid rgba(148, 163, 184, 0.18);
        background: rgba(15, 23, 42, 0.72);
        box-shadow: 0 18px 55px rgba(15, 23, 42, 0.3);
        margin-bottom: 1rem;
    }

    .surface h2,
    .surface h3 {
        margin-top: 0;
    }

    .preview-box {
        margin-top: 1rem;
        padding: 1rem;
        border-radius: 22px;
        background: rgba(2, 6, 23, 0.45);
        border: 1px solid rgba(148, 163, 184, 0.16);
    }

    .tip-card {
        padding: 1rem;
        border-radius: 18px;
        background: rgba(30, 41, 59, 0.78);
        border: 1px solid rgba(148, 163, 184, 0.16);
        margin-bottom: 0.8rem;
    }

    .stMetric {
        background: rgba(15, 23, 42, 0.72);
        border: 1px solid rgba(148, 163, 184, 0.16);
        border-radius: 18px;
        padding: 0.8rem 0.9rem;
    }

    .stButton > button {
        border-radius: 999px;
        border: 1px solid rgba(59, 130, 246, 0.35);
        background: linear-gradient(135deg, #38bdf8, #2563eb);
        color: white;
        font-weight: 700;
        padding: 0.72rem 1.15rem;
    }

    .stDownloadButton > button {
        border-radius: 999px;
        border: 1px solid rgba(34, 197, 94, 0.35);
        background: linear-gradient(135deg, #22c55e, #16a34a);
        color: white;
        font-weight: 700;
        padding: 0.72rem 1.15rem;
    }

    div[data-testid="stFileUploader"] {
        background: rgba(15, 23, 42, 0.72);
        border-radius: 24px;
        border: 1px dashed rgba(148, 163, 184, 0.35);
        padding: 0.9rem;
    }

    footer {
        visibility: hidden;
    }
</style>
"""


def render_footer() -> None:
    st.markdown("<div style='margin-top: 1.2rem; color: #94a3b8;'>Created by Matias Barra</div>", unsafe_allow_html=True)


def render_hero() -> None:
    st.markdown(
        """
        <div class="hero">
            <div class="eyebrow">Web PDF converter</div>
            <h1>Turn dark notes into a clean printable PDF.</h1>
            <p>
                Upload a PDF, tune the inversion settings if needed, and export a version that is easier to print,
                review, or archive. Everything runs directly in the browser.
            </p>
            <div class="pill-row">
                <div class="pill">Smart color preservation</div>
                <div class="pill">Black and white mode</div>
                <div class="pill">Fast browser-based flow</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_side_tips() -> None:
    st.markdown(
        """
        <div class="tip-card">
            <strong>Recommended flow</strong><br>
            Start with <em>smart</em> mode, keep DPI at 450, and only change thresholds if the previewed result
            would be too dark or too aggressive for your PDF.
        </div>
        <div class="tip-card">
            <strong>Best when</strong><br>
            You want to convert handwritten or annotated notes into a version that prints on white paper without
            losing colored highlights.
        </div>
        <div class="tip-card">
            <strong>If the file is huge</strong><br>
            Lower DPI to 300 first. It usually reduces file size while keeping the output readable.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_preview_notice() -> None:
    st.markdown(
        "<div class='preview-box'><strong>Preview</strong><br>The preview shows the first page using the current settings.</div>",
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def get_preview_image(
    pdf_bytes: bytes,
    dpi: int,
    bg_value_threshold: int,
    light_value_threshold: int,
    neutral_color_threshold: int,
    mode: str,
    bw_threshold: int,
):
    return preview_first_page(
        pdf_bytes=pdf_bytes,
        dpi=dpi,
        bg_value_threshold=bg_value_threshold,
        light_value_threshold=light_value_threshold,
        neutral_color_threshold=neutral_color_threshold,
        mode=mode,
        bw_threshold=bw_threshold,
    )


def main() -> None:
    st.set_page_config(page_title="PDF Inverter", page_icon="PDF", layout="wide")
    st.markdown(APP_STYLE, unsafe_allow_html=True)

    for key, value in DEFAULT_SETTINGS.items():
        if key not in st.session_state:
            st.session_state[key] = value

    render_hero()

    main_col, side_col = st.columns([1.45, 0.85], gap="large")

    with side_col:
        st.markdown("<div class='surface'>", unsafe_allow_html=True)
        st.subheader("Conversion settings")

        if st.button("Reset settings"):
            for key, value in DEFAULT_SETTINGS.items():
                st.session_state[key] = value
            st.rerun()

        mode = st.selectbox("Mode", ["smart", "bw"], key="mode")
        dpi = st.selectbox("DPI", [300, 450, 600], key="dpi")
        bg_value_threshold = st.slider("Dark threshold", 0, 255, key="bg_value_threshold")
        light_value_threshold = st.slider("Light threshold", 0, 255, key="light_value_threshold")
        neutral_color_threshold = st.slider("Neutral threshold", 0, 100, key="neutral_color_threshold")
        bw_threshold = st.slider("B/W threshold", 0, 255, key="bw_threshold")
        jpeg_quality = st.slider(
            "JPEG quality",
            min_value=50,
            max_value=95,
            help="Higher value means better quality and a larger file. 85 is a good default.",
            key="jpeg_quality",
        )
        st.markdown("</div>", unsafe_allow_html=True)

        render_side_tips()

    with main_col:
        st.markdown("<div class='surface'>", unsafe_allow_html=True)
        st.subheader("Upload your PDF")
        st.caption("Drag and drop a file or browse from your computer.")
        uploaded = st.file_uploader("Choose a PDF", type=["pdf"], label_visibility="collapsed")

        if uploaded is None:
            st.info("No PDF selected yet.")
            st.markdown("</div>", unsafe_allow_html=True)
            render_footer()
            return

        pdf_bytes = uploaded.getvalue()
        size_kb = len(pdf_bytes) / 1024 if pdf_bytes else 0
        info_col1, info_col2, info_col3 = st.columns(3)
        info_col1.metric("File", uploaded.name)
        info_col2.metric("Size", f"{size_kb:.1f} KB")
        info_col3.metric("Mode", "Smart" if mode == "smart" else "B/W")

        st.success(f"Ready to convert: {uploaded.name}")

        render_preview_notice()

        try:
            preview_image = get_preview_image(
                pdf_bytes=pdf_bytes,
                dpi=dpi,
                bg_value_threshold=bg_value_threshold,
                light_value_threshold=light_value_threshold,
                neutral_color_threshold=neutral_color_threshold,
                mode=mode,
                bw_threshold=bw_threshold,
            )
            st.image(preview_image, caption="First page preview", use_container_width=True)
        except Exception as exc:
            st.warning(f"Preview unavailable: {exc}")

        convert_pressed = st.button("Convert PDF", type="primary", use_container_width=True)

        if convert_pressed:
            with st.spinner("Processing PDF..."):
                try:
                    output_bytes = process_pdf_bytes(
                        pdf_bytes=pdf_bytes,
                        dpi=dpi,
                        bg_value_threshold=bg_value_threshold,
                        light_value_threshold=light_value_threshold,
                        neutral_color_threshold=neutral_color_threshold,
                        mode=mode,
                        bw_threshold=bw_threshold,
                        jpeg_quality=jpeg_quality,
                    )
                except Exception as exc:
                    st.error(f"Error processing PDF: {exc}")
                    st.markdown("</div>", unsafe_allow_html=True)
                    render_footer()
                    return

            output_name = suggested_output_name(uploaded.name, mode)
            download_col, message_col = st.columns([1, 1])
            with download_col:
                st.download_button(
                    label="Download converted PDF",
                    data=output_bytes,
                    file_name=output_name,
                    mime="application/pdf",
                    use_container_width=True,
                )
            with message_col:
                st.success("Conversion complete")

        st.markdown("</div>", unsafe_allow_html=True)

    render_footer()


if __name__ == "__main__":
    main()