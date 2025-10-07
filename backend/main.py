from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import openai
import os
from dotenv import load_dotenv
import base64
from PIL import Image
import pytesseract
import io

app = FastAPI()

# Allow CORS for local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load environment variables from .env file
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY


class DescriptionResponse(BaseModel):
    # New structured fields for product listing
    product_name: Optional[str] = None
    product_description: Optional[str] = None
    product_category: Optional[str] = None
    product_subcategory: Optional[str] = None
    highlights: Optional[List[str]] = None
    # Backward/compat fields
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    holiday: Optional[str] = None


@app.post("/describe", response_model=DescriptionResponse)
async def describe_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File is not an image.")
    image_bytes = await file.read()
    try:
        # OCR: Extract text from image
        ocr_text = ""
        try:
            image = Image.open(io.BytesIO(image_bytes))
            ocr_text = pytesseract.image_to_string(image)
        except Exception:
            ocr_text = ""

        # Encode image as base64 and create data URL
        encoded = base64.b64encode(image_bytes).decode()
        mime_type = file.content_type
        data_url = f"data:{mime_type};base64,{encoded}"
        # Allowed product categories (exact string match required)
        allowed_categories = [
            "Baking Supplies","Kitchen Accessories","Holiday Costumes","Character Costumes","Costume Accessories",
            "Pet Costumes","Albums","Women","Bath & Body","Books","Movies & Music","Stuffed Animals",
            "Toys & Games","Pawlidays™ Pet Lovers","Personalized Products","Stationery","Gift Wrap",
            "Cellophane Bags","Gift Card Holders","Fillers","Ribbons & Bows","Tissue Paper","Specialty Supplies",
            "Seasonal Storage","Crafting","Costumes","Party Supplies","Home Decor","Stationery & Packaging",
            "Garden & Outdoor","Fashion","Gifts & Keepsakes","Seasonal Crafting","DIY Kits","Men","Kids",
            "Tableware","Dinnerware","Drinkware","Barware","Serveware","Party Favors","Backdrops & Signage",
            "Banners & Flags","Candles & Votives","Ceiling Décor","Centerpieces & Table Décor","Chair Covers",
            "Confetti","Decorating Fabrics","Door Banners, Curtains & Fringe","Garland","Lighting","Paper Lanterns",
            "Wall Decorations","Window Clings","Photo Booths","Apparel","Shoes","Accessories","Decorations",
            "Balloons","Crafts & DIY","Baking & Cooking"
        ]
        allowed_categories_text = "\n- " + "\n- ".join(allowed_categories)

        # Prompt now asks for structured product fields using allowed categories
        system_prompt = (
            "You are an assistant for online sellers. For any product image and its extracted text, return structured data in JSON. "
            "You MUST choose productCategory as EXACTLY ONE of the following allowed values (case-sensitive):\n"
            f"{allowed_categories_text}\n\n"
            "If the product fits 'Holiday Decor', also set a 'holiday' field with the specific holiday (e.g., Christmas, Halloween, Easter, Diwali). "
            "Rules:\n"
            "- productName: a concise, buyer-friendly title.\n"
            "- productDescription: a concise 1-2 sentence description.\n"
            "- productCategory: one from the allowed list above.\n"
            "- productSubcategory: a more specific subcategory if obvious (text), else null.\n"
            "- highlights: concise 1 line highlighting feature of product.\n"
            "- tags: 5-8 short keywords (array of strings).\n"
            "- holiday: string if detected (e.g., Diwali), else null.\n"
            "Respond ONLY valid minified JSON with these keys: productName, productDescription, productCategory, productSubcategory, highlights, tags, brand, holiday."
        )
        user_content = [
            {"type": "text", "text": (
                "Using the image and the extracted text below, produce the JSON as specified. "
                f"\n\nExtracted text from image (OCR): {ocr_text.strip()}"
            )},
            {"type": "image_url", "image_url": {"url": data_url}}
        ]
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=300
        )
        import json
        import re
        # Try to parse the model's response as JSON
        content = response.choices[0].message.content.strip()
        try:
            result = json.loads(content)
            product_name = result.get("productName")
            product_description = result.get("productDescription")
            product_category = result.get("productCategory")
            product_subcategory = result.get("productSubcategory")
            highlights = result.get("highlights") or []
            tags = result.get("tags") or []
            holiday = result.get("holiday")
            # Back-compat mapping
            description = product_description or ""
            category = product_category
        except Exception:
            # Fallback: try to extract minimal fields from JSON-like string
            product_name = None
            product_description = None
            product_category = None
            product_subcategory = None
            highlights = []
            tags = []
            brand = None
            holiday = None
            category = None
            description = content
            # Attempt regex extraction for a few keys
            name_match = re.search(r'"productName"\s*:\s*"([^"]+)"', content)
            if name_match:
                product_name = name_match.group(1)
            desc_match = re.search(r'"productDescription"\s*:\s*"([^"]+)"', content)
            if desc_match:
                product_description = desc_match.group(1)
                description = product_description
            cat_match = re.search(r'"productCategory"\s*:\s*"([^"]+)"', content)
            if cat_match:
                product_category = cat_match.group(1)
                category = product_category
            subcat_match = re.search(r'"productSubcategory"\s*:\s*(null|"([^"]*)")', content)
            if subcat_match and subcat_match.group(1) != 'null':
                product_subcategory = subcat_match.group(2)
            tags_match = re.search(r'"tags"\s*:\s*\[(.*?)\]', content, re.DOTALL)
            if tags_match:
                tags = re.findall(r'"([^"]+)"', tags_match.group(1))
            hl_match = re.search(r'"highlights"\s*:\s*\[(.*?)\]', content, re.DOTALL)
            if hl_match:
                highlights = re.findall(r'"([^"]+)"', hl_match.group(1))
            brand_match = re.search(r'"brand"\s*:\s*(null|"([^"]*)")', content)
            if brand_match and brand_match.group(1) != 'null':
                brand = brand_match.group(2)
            holiday_match = re.search(r'"holiday"\s*:\s*(null|"([^"]*)")', content)
            if holiday_match and holiday_match.group(1) != 'null':
                holiday = holiday_match.group(2)

        return {
            # New fields
            "product_name": product_name,
            "product_description": product_description or description,
            "product_category": product_category,
            "product_subcategory": product_subcategory,
            "highlights": highlights,
            # Back-compat fields
            "description": description,
            "tags": tags,
            "brand": brand,
            "category": category,
            "holiday": holiday,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
