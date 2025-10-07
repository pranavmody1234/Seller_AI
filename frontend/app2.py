import streamlit as st
import requests

st.set_page_config(page_title="Seller Listing Helper (Blip3)", page_icon="🛒", layout="centered")

st.markdown("""
<style>
.tag-badge {
    display: inline-block;
    background: #f0f2f6;
    color: #333;
    border-radius: 12px;
    padding: 0.25em 0.75em;
    margin: 0.15em;
    font-size: 0.95em;
    border: 1px solid #e0e0e0;
}
</style>
""", unsafe_allow_html=True)

st.header("Seller Listing AI (Using Blip3)")
st.write("Upload a product image to instantly generate a one-line description using Blip3.")

with st.container():
    col1, col2 = st.columns([1,2])
    with col1:
        uploaded_files = st.file_uploader("Product Images (up to 4)", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True, help="You can upload up to 4 images.")
    with col2:
        st.markdown("**How it works:**\n\n1. Upload your product image.\n2. Click 'Generate Listing Description'.\n3. Copy the AI-generated description for your listing.")

if uploaded_files:
    st.image([f for f in uploaded_files], caption=[f"Preview {i+1}" for i in range(len(uploaded_files))], use_container_width=True)
    if st.button("Generate Listing Description", use_container_width=True):
        with st.spinner("Analyzing images and generating listing..."):
            files = [("file", (f.name, f, f.type)) for f in uploaded_files]
            try:
                # Only send the first image for now (Blip3 API expects one image)
                response = requests.post(
                    "http://localhost:8000/describe",
                    files={"file": (uploaded_files[0].name, uploaded_files[0], uploaded_files[0].type)},
                    timeout=120
                )
                if response.status_code == 200:
                    data = response.json()
                    description = data.get("description", "")
                    st.subheader("Listing Description")
                    st.write(description)
                else:
                    st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
            except Exception as e:
                st.error(f"Request failed: {e}")
