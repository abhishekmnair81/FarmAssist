import asyncio
import time
from app.services.vision_service import diagnose_plant_disease

async def main():
    print("========================================")
    print("STARTING END-TO-END VISION SERVICE TESTS")
    print("========================================")

    # 1. Test Chemical Packet (Shriram Fipro)
    with open("/app/test_chem.jpg", "rb") as f:
        chem_bytes = f.read()

    start = time.time()
    print("\n[TEST 1] Agrochemical Packet (Shriram Fipro) in English...")
    res1 = await diagnose_plant_disease(
        chem_bytes,
        caption="How much should I apply for paddy stem borer?",
        language="English"
    )
    print(f"Time taken: {time.time()-start:.2f}s")
    print("RESULT 1:\n", res1, "\n")

    # 2. Test Agrochemical in Malayalam
    start = time.time()
    print("\n[TEST 2] Agrochemical Packet (Shriram Fipro) in Malayalam...")
    res2 = await diagnose_plant_disease(
        chem_bytes,
        caption="ഇത് നെല്ലിൽ എപ്പോൾ എങ്ങനെ ഉപയോഗിക്കണം?",
        language="Malayalam"
    )
    print(f"Time taken: {time.time()-start:.2f}s")
    print("RESULT 2:\n", res2, "\n")

    # 3. Test Non-Agricultural Image
    with open("/app/test_other.jpg", "rb") as f:
        other_bytes = f.read()

    start = time.time()
    print("\n[TEST 3] Non-Agricultural Image (Laptop)...")
    res3 = await diagnose_plant_disease(
        other_bytes,
        caption="What is this?",
        language="English"
    )
    print(f"Time taken: {time.time()-start:.2f}s")
    print("RESULT 3:\n", res3)

if __name__ == "__main__":
    asyncio.run(main())
