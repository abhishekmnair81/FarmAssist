import asyncio
import io
import time
from PIL import Image, ImageDraw
from app.services.vision_service import diagnose_plant_disease

async def test_leaf():
    print("=== TESTING REALISTIC CROP LEAF PATHOLOGY ===")
    # Create a realistic leaf representation with distinct fungal blight target lesions
    img = Image.new("RGB", (600, 600), color=(46, 139, 87)) # Sea green leaf surface
    d = ImageDraw.Draw(img)
    # Draw leaf vein network
    d.line([(300, 50), (300, 550)], fill=(34, 100, 60), width=6)
    d.line([(300, 200), (120, 120)], fill=(34, 100, 60), width=4)
    d.line([(300, 320), (480, 240)], fill=(34, 100, 60), width=4)
    d.line([(300, 420), (140, 360)], fill=(34, 100, 60), width=4)
    
    # Target concentric ring fungal lesions (Alternaria / Cercospora)
    # Lesion 1
    d.ellipse([180, 180, 280, 280], fill=(218, 165, 32)) # Yellow chlorotic halo
    d.ellipse([195, 195, 265, 265], fill=(139, 69, 19)) # Brown necrotic zone
    d.ellipse([210, 210, 250, 250], fill=(70, 35, 10))  # Dark brown center
    d.ellipse([220, 220, 240, 240], fill=(20, 10, 5))   # Bullseye ring
    
    # Lesion 2
    d.ellipse([340, 260, 440, 360], fill=(218, 165, 32))
    d.ellipse([355, 275, 425, 345], fill=(139, 69, 19))
    d.ellipse([370, 290, 410, 330], fill=(70, 35, 10))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    leaf_bytes = buf.getvalue()

    start = time.time()
    res = await diagnose_plant_disease(
        leaf_bytes,
        caption="My tomato plants have these circular brown spots on the leaves. What is it and how do I cure it?",
        language="English"
    )
    print(f"Leaf diagnosis completed in {time.time()-start:.2f}s:")
    print("================================================")
    print(res)
    print("================================================")

if __name__ == "__main__":
    asyncio.run(test_leaf())
