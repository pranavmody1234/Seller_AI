import replicate
import os
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image
import io
import base64

load_dotenv()
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")


app = FastAPI()
app2 = FastAPI()


for _app in (app, app2):
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

class BlipResponse(BaseModel):
    description: str
    category: str | None = None
    holiday: str | None = None
    brand: str | None = None
    tags: list[str] | None = None

@app.post("/describe", response_model=BlipResponse)
@app2.post("/describe", response_model=BlipResponse)
async def describe_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File is not an image.")
    image_bytes = await file.read()
    try:
        # Save image to a temporary file for Replicate
        image = Image.open(io.BytesIO(image_bytes))
        temp_path = "temp_image.png"
        image.save(temp_path)
        os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN
        # Prompt Blip3 to respond in JSON
        prompt = (
            "Describe this product for a marketplace listing. Respond in JSON with keys: description (one line), category, holiday (if any), brand (if any), tags (list of keywords)."
        )
        output = replicate.run(
            "zsxkib/blip-3:499bec581d8f64060fd695ec0c34d7595c6824c4118259aa8b0788e0d2d903e1",
            input={"image": open(temp_path, "rb"), "prompt": prompt}
        )
        os.remove(temp_path)
        import json
        description = None
        category = None
        holiday = None
        brand = None
        tags = None
        if isinstance(output, list):
            output_str = output[0]
        else:
            output_str = str(output)
        try:
            result = json.loads(output_str)
            description = result.get("description", output_str)
            category = result.get("category")
            holiday = result.get("holiday")
            brand = result.get("brand")
            tags = result.get("tags")
        except Exception:
            description = output_str
        return {
            "description": description,
            "category": category,
            "holiday": holiday,
            "brand": brand,
            "tags": tags
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
