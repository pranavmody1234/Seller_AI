import streamlit as st
import requests
import json

st.set_page_config(page_title="Seller Listing Helper", page_icon="🛒", layout="centered")

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

st.header("Seller Listing AI")
st.write("Upload a product image to generate a structured product listing: name, description, category, subcategory, highlights, and tags.")

# Backend config
backend_url = st.sidebar.text_input("Backend URL", value="http://localhost:8000", help="Change to http://localhost:8001 if your backend runs on 8001.")


with st.container():
    col1, col2 = st.columns([1,2])
    with col1:
        uploaded_files = st.file_uploader("Product Images (up to 4)", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True, help="You can upload up to 4 images.")
    with col2:
        st.markdown("**How it works:**\n\n1. Upload your product image.\n2. Click 'Generate Listing Description'.\n3. Copy the AI-generated description and tags for your listing.")

if uploaded_files:
    st.image([f for f in uploaded_files], caption=[f"Preview {i+1}" for i in range(len(uploaded_files))], use_container_width=True)
    st.caption("Note: For now, only the first image is analyzed.")
    if st.button("Generate Listing", use_container_width=True):
        with st.spinner("Analyzing image and generating listing..."):
            primary = uploaded_files[0]
            files = {"file": (primary.name, primary, primary.type)}
            try:
                response = requests.post(
                    f"{backend_url}/describe",
                    files=files,
                    timeout=120
                )
                if response.status_code == 200:
                    data = response.json()
                    # New fields (with graceful fallbacks)
                    product_name = data.get("product_name")
                    product_description = data.get("product_description") or data.get("description", "")
                    product_category = data.get("product_category") or data.get("category")
                    product_subcategory = data.get("product_subcategory")
                    highlights = data.get("highlights") or []
                    tags = data.get("tags", [])
                    brand = data.get("brand")
                    holiday = data.get("holiday")

                    if product_name:
                        st.subheader("Product Name")
                        st.info(product_name)

                    if product_category or product_subcategory:
                        st.subheader("Category")
                        if product_category:
                            st.write(f"Product Category: {product_category}")
                        if product_subcategory:
                            st.write(f"Product Subcategory: {product_subcategory}")

                    if brand:
                        st.subheader("Brand")
                        st.info(brand)
                    if holiday:
                        st.subheader("Holiday")
                        st.info(holiday)

                    st.subheader("Product Description")
                    st.write(product_description)

                    if highlights:
                        st.subheader("Highlights")
                        for h in highlights:
                            st.markdown(f"- {h}")

                    st.subheader("Suggested Tags")
                    if tags:
                        tag_html = " ".join([f'<span class="tag-badge">{tag}</span>' for tag in tags])
                        st.markdown(tag_html, unsafe_allow_html=True)
                        st.caption("Copy and paste these tags into your listing.")
                    else:
                        st.info("No tags generated.")
                else:
                    # Try to show server-provided error detail
                    try:
                        st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                    except Exception:
                        st.error(f"HTTP {response.status_code}")
            except Exception as e:
                st.error(f"Request failed: {e}")
