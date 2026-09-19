"""
Agrochemical Knowledge Base for Indian Agriculture (CIBRC Standard).
Provides verified intelligence on active ingredients, brands, approved crops,
target pests, official dosage per liter/acre, application methods, safety, and PHI.
"""

import re
from typing import Optional, Dict, Any

AGROCHEMICAL_DATABASE: Dict[str, Dict[str, Any]] = {
    "chlorpyrifos": {
        "chemical_name": "Chlorpyrifos 20% EC / 50% EC / 50% + Cypermethrin 5% EC",
        "popular_brands": ["RAMBO-50", "Dursban", "Tafaban", "Classic 20", "Radar", "Lethal", "Chloroguard"],
        "classification": "Broad-Spectrum Organophosphate Insecticide & Acaricide",
        "mode_of_action": "Contact, stomach, and respiratory/fumigant action. Inhibits acetylcholinesterase in insect nervous systems.",
        "approved_crops": "Paddy (Rice), Cotton, Sugarcane, Wheat, Maize, Groundnut, Vegetables (Brinjal, Cabbage, Tomato), Fruit Trees (Citrus, Mango), and Non-crop Termite Control.",
        "target_pests": "Stem Borer, Leaf Folder, Gall Midge, Hispa, Bollworms, Aphids, Whiteflies, Thrips, Cutworms, Root Grubs, Termites (White Ants).",
        "dosage_foliar": "2.0 ml to 2.5 ml per liter of water (400 to 500 ml per acre dissolved in 200 liters of water).",
        "dosage_soil": "3.0 ml to 4.0 ml per liter of water (1.0 to 1.5 liters per acre in irrigation water for soil termites and root grubs).",
        "when_to_apply": "Apply at the early appearance of insect pests. Spray during early morning (6–9 AM) or late afternoon (4–6 PM). Avoid spraying in peak sunlight or during strong winds.",
        "phi_days": "15 to 21 days for cotton and paddy; 7 to 10 days for vegetables.",
        "toxicity_level": "Yellow Triangle (Highly Toxic). Handle with strict precautions.",
        "safety_ppe": "Wear chemical-resistant rubber gloves, face mask, eye goggles, and full-sleeved protective clothing. Never eat, drink, or smoke during mixing or spraying.",
        "tank_mix_cautions": "Compatible with most non-alkaline insecticides and fungicides. Do NOT mix with Bordeaux mixture, lime sulphur, or alkaline chemicals."
    },
    "imidacloprid": {
        "chemical_name": "Imidacloprid 17.8% SL / 30.5% SC / 70% WG",
        "popular_brands": ["Confidor", "Tatamida", "Victor", "Imida", "Media", "Admire"],
        "classification": "Systemic Neonicotinoid Insecticide",
        "mode_of_action": "Systemic and translaminar action. Disrupts transmission of nervous impulses across acetylcholine receptors.",
        "approved_crops": "Cotton, Paddy, Chilli, Tomato, Okra, Brinjal, Mango, Citrus, Sugarcane, Groundnut.",
        "target_pests": "Aphids, Jassids, Whiteflies, Thrips, Brown Plant Hopper (BPH), Green Leaf Hopper (GLH), Termites.",
        "dosage_foliar": "0.3 ml to 0.5 ml per liter of water (60 to 100 ml per acre in 150–200 liters of water for 17.8% SL).",
        "dosage_soil": "1.0 ml per liter for seed treatment or nursery root dip.",
        "when_to_apply": "At pest ETL (Economic Threshold Level). Best applied at vegetative to early flowering stage when sucking pest populations begin building up.",
        "phi_days": "21 days for paddy, 40 days for cotton, 3 to 5 days for vegetables.",
        "toxicity_level": "Blue Triangle (Moderately Toxic). Toxic to honeybees; avoid spraying during active honeybee pollination hours.",
        "safety_ppe": "Wear rubber gloves and protective mask.",
        "tank_mix_cautions": "Compatible with common fungicides like Mancozeb, Hexaconazole, and Carbendazim."
    },
    "chlorantraniliprole": {
        "chemical_name": "Chlorantraniliprole 18.5% SC",
        "popular_brands": ["Coragen", "Cosko", "Cover", "Voliam Flexi"],
        "classification": "Anthranilic Diamide Insecticide (Ryanodine Receptor Modulator)",
        "mode_of_action": "Translaminar and systemic activity. Activates insect ryanodine receptors causing rapid muscle contraction, cessation of feeding, and death.",
        "approved_crops": "Paddy (Rice), Sugarcane, Cotton, Maize, Tomato, Chilli, Cabbage, Pigeon pea, Bengal gram, Soybean.",
        "target_pests": "Yellow Stem Borer, Leaf Folder, Fall Armyworm (FAW), Early Shoot Borer, Top Borer, American Bollworm (Helicoverpa), Diamondback Moth (DBM), Fruit Borer.",
        "dosage_foliar": "0.3 ml to 0.4 ml per liter of water (60 ml per acre in 150–200 liters of water).",
        "dosage_soil": "Not recommended for general soil drenching; primarily foliar application.",
        "when_to_apply": "Apply at the egg-laying or early instar larvae emergence stage for maximum prevention.",
        "phi_days": "3 days for tomato and chilli; 14 days for paddy; 21 days for sugarcane.",
        "toxicity_level": "Green Triangle (Slightly Toxic). Very safe for beneficial predators and parasitoids.",
        "safety_ppe": "Wear standard protective goggles and face mask during spraying.",
        "tank_mix_cautions": "Highly compatible with most neutral fungicides and fertilizers."
    },
    "mancozeb": {
        "chemical_name": "Mancozeb 75% WP",
        "popular_brands": ["Dithane M-45", "Indofil M-45", "Uthane", "Abic M-45"],
        "classification": "Broad-Spectrum Contact Dithiocarbamate Fungicide",
        "mode_of_action": "Multi-site contact protective action. Inhibits enzyme sulfhydryl groups in fungal respiration and spore germination.",
        "approved_crops": "Tomato, Potato, Paddy, Chilli, Grapes, Apple, Banana, Groundnut, Wheat, Maize, Onion, Guava.",
        "target_pests": "Early Blight, Late Blight, Blast, Brown Spot, Leaf Spot (Cercospora, Alternaria), Anthracnose, Downy Mildew, Rust, Fruit Rot / Die-back.",
        "dosage_foliar": "2.0 g to 2.5 g per liter of water (400 to 500 g per acre in 200 liters of water).",
        "dosage_soil": "Seed treatment @ 3 g per kg seed.",
        "when_to_apply": "Preventive spray before disease onset or immediately when first spots appear. Repeat every 7–10 days during cloudy/humid conditions.",
        "phi_days": "7 days for vegetables, 14 days for fruits and cereals.",
        "toxicity_level": "Green Triangle (Slightly Toxic).",
        "safety_ppe": "Use dust mask and goggles to prevent inhalation of fine wettable powder.",
        "tank_mix_cautions": "Compatible with most insecticides and systemic fungicides. Do NOT mix with lime sulphur or alkaline sprays."
    },
    "carbendazim_mancozeb": {
        "chemical_name": "Carbendazim 12% + Mancozeb 63% WP",
        "popular_brands": ["Saaf", "Sixer", "Sprint", "Companion"],
        "classification": "Dual Action (Systemic + Contact) Fungicide",
        "mode_of_action": "Carbendazim acts systemically through xylem; Mancozeb provides multi-site protective contact barrier.",
        "approved_crops": "Groundnut, Paddy, Chilli, Tomato, Potato, Tea, Grapes, Mango, Soybean, Vegetables.",
        "target_pests": "Blast, Sheath Blight, Tikka Leaf Spot, Early & Late Blight, Anthracnose, Powdery Mildew, Collar Rot, Root Rot.",
        "dosage_foliar": "2.0 g per liter of water (400 g per acre in 200 liters of water).",
        "dosage_soil": "Seed treatment: 2.5 g/kg seed. Soil drenching: 3 g/L around root zone.",
        "when_to_apply": "Apply at early symptom emergence or as prophylactic spray before anticipated fungal outbreaks.",
        "phi_days": "14 to 21 days depending on crop.",
        "toxicity_level": "Blue Triangle (Moderately Toxic).",
        "safety_ppe": "Standard PPE (gloves, mask, protective apron).",
        "tank_mix_cautions": "Compatible with common neutral insecticides like Imidacloprid, Thiamethoxam, and Chlorpyrifos."
    },
    "glyphosate": {
        "chemical_name": "Glyphosate 41% SL",
        "popular_brands": ["Roundup", "Glycel", "Weedoff", "Sweep", "Uproot"],
        "classification": "Non-Selective Systemic Post-Emergence Herbicide",
        "mode_of_action": "Systemic translocated herbicide. Inhibits EPSP synthase enzyme, halting synthesis of essential aromatic amino acids.",
        "approved_crops": "Tea, Non-crop open land, Bunds, Water channels, Orchards (directed spray under tree canopy). NEVER spray directly on standing green crops.",
        "target_pests": "Annual and perennial grasses, broadleaf weeds, sedges (Cyperus rotundus, Cynodon dactylon, Parthenium).",
        "dosage_foliar": "8 ml to 10 ml per liter of water (1.0 to 1.5 liters per acre in 150 liters of clean, silt-free water).",
        "dosage_soil": "No soil activity (rapidly deactivated by soil particles).",
        "when_to_apply": "Apply on actively growing green weeds (15–20 cm tall) during sunny weather. Ensure 4–6 hours rain-free period after spray.",
        "phi_days": "Non-crop/directed spray only. Do not let spray drift touch green bark, foliage, or crop stems.",
        "toxicity_level": "Blue Triangle (Moderately Toxic).",
        "safety_ppe": "Wear rubber gloves, protective clothing, and face shield. Use floodjet or deflector nozzle with spray hood to avoid drift.",
        "tank_mix_cautions": "Mix with clean water only (muddy/silty water deactivates glyphosate). Add 1% ammonium sulphate to enhance efficacy."
    },
    "hexaconazole": {
        "chemical_name": "Hexaconazole 5% SC / 5% EC",
        "popular_brands": ["Contaf Plus", "Sitara", "Glow", "Hexa"],
        "classification": "Systemic Triazole Ergosterol Biosynthesis Inhibitor Fungicide",
        "mode_of_action": "Systemic with protective, curative, and eradicative properties. Rapidly absorbed and translocated acropetally.",
        "approved_crops": "Paddy, Chilli, Grapes, Mango, Apple, Groundnut, Soybean.",
        "target_pests": "Sheath Blight, Powdery Mildew, Anthracnose, Leaf Spot, Rust, Scab.",
        "dosage_foliar": "2.0 ml per liter of water (400 ml per acre in 200 liters of water).",
        "dosage_soil": "Foliar application only.",
        "when_to_apply": "Spray at first sign of disease. Highly effective curative against powdery mildew and sheath blight.",
        "phi_days": "15 to 20 days.",
        "toxicity_level": "Blue Triangle (Moderately Toxic).",
        "safety_ppe": "Standard safety gloves and face mask.",
        "tank_mix_cautions": "Compatible with most commonly used insecticides."
    },
    "azoxystrobin_difenoconazole": {
        "chemical_name": "Azoxystrobin 18.2% + Difenoconazole 11.4% SC",
        "popular_brands": ["Amistar Top", "Custodia", "Mirador Duo"],
        "classification": "Broad-Spectrum Strobilurin + Triazole Fungicide",
        "mode_of_action": "Dual mode of action: inhibits mitochondrial respiration (QoI) and sterol demethylation (DMI).",
        "approved_crops": "Paddy, Tomato, Chilli, Maize, Wheat, Onion, Grapes.",
        "target_pests": "Blast, Sheath Blight, Early Blight, Late Blight, Anthracnose, Powdery Mildew, Purple Blotch.",
        "dosage_foliar": "1.0 ml per liter of water (200 ml per acre in 200 liters of water).",
        "dosage_soil": "Foliar application only.",
        "when_to_apply": "At early infection or as preventative spray before humid rain events.",
        "phi_days": "5 days for tomato and chilli, 14 days for paddy.",
        "toxicity_level": "Blue Triangle (Moderately Toxic).",
        "safety_ppe": "Standard protective eyewear and gloves.",
        "tank_mix_cautions": "Do not mix with calcium nitrate or organosilicone surfactants."
    },
    "thiamethoxam": {
        "chemical_name": "Thiamethoxam 25% WG",
        "popular_brands": ["Actara", "Extra", "Areva", "Anant"],
        "classification": "Second Generation Neonicotinoid Systemic Insecticide",
        "mode_of_action": "Systemic contact and stomach action with high root and foliar absorption.",
        "approved_crops": "Rice, Cotton, Wheat, Mustard, Tomato, Okra, Brinjal, Potato, Tea, Citrus.",
        "target_pests": "Aphids, Jassids, Whiteflies, Thrips, Stem Borer, Green Leaf Hopper, Gall Midge, Mosquito Bug.",
        "dosage_foliar": "0.5 g per liter of water (80 to 100 g per acre in 150–200 liters of water).",
        "dosage_soil": "Soil drenching: 1.0 g per liter around root zone for nursery vigor and sucking pest protection.",
        "when_to_apply": "Apply at early vegetative stage or on appearance of sucking pests.",
        "phi_days": "14 days for rice, 21 days for cotton, 5 days for vegetables.",
        "toxicity_level": "Green Triangle (Slightly Toxic). Highly toxic to bees; do not spray during flowering.",
        "safety_ppe": "Face mask and gloves.",
        "tank_mix_cautions": "Compatible with most standard fungicides."
    },
    "emamectin_benzoate": {
        "chemical_name": "Emamectin Benzoate 5% SG",
        "popular_brands": ["Proclaim", "EM-1", "Safari", "King Claim"],
        "classification": "Macrocyclic Avermectin Bio-Insecticide",
        "mode_of_action": "Strong translaminar, stomach, and contact action. Paralyzes neuromuscular transmission by binding GABA receptors.",
        "approved_crops": "Cotton, Okra, Cabbage, Chilli, Brinjal, Tomato, Chickpea, Pigeonpea, Tea, Maize.",
        "target_pests": "Bollworms, Fruit and Shoot Borer, Diamondback Moth (DBM), Fall Armyworm (FAW), Pod Borer (Helicoverpa), Thrips.",
        "dosage_foliar": "0.5 g per liter of water (80 to 100 g per acre in 200 liters of water).",
        "dosage_soil": "Foliar application only.",
        "when_to_apply": "Spray at early instar caterpillar hatching or first sign of boreholes in fruits/pods.",
        "phi_days": "3 days for vegetables, 14 days for cotton and pulses.",
        "toxicity_level": "Blue Triangle (Moderately Toxic). Safe for beneficial insects once dried.",
        "safety_ppe": "Dust mask and gloves while preparing spray solution.",
        "tank_mix_cautions": "Compatible with most neutral agricultural chemicals."
    },
    "copper_oxychloride": {
        "chemical_name": "Copper Oxychloride 50% WP",
        "popular_brands": ["Blitox", "Fytolan", "Blue Copper", "Cupramar"],
        "classification": "Broad-Spectrum Protective Inorganic Copper Fungicide & Bactericide",
        "mode_of_action": "Multi-site contact fungicide and bactericide. Denatures fungal and bacterial proteins on plant surfaces.",
        "approved_crops": "Paddy, Tomato, Potato, Chilli, Citrus, Coffee, Cardamom, Banana, Grapes, Mango.",
        "target_pests": "Bacterial Blight, Canker, Late Blight, Downy Mildew, Rust, Leaf Spot, Fruit Rot, Dieback, Sigatoka.",
        "dosage_foliar": "2.5 g to 3.0 g per liter of water (500 to 600 g per acre in 200 liters of water).",
        "dosage_soil": "Soil drenching for root rot/wilt @ 3 g/L.",
        "when_to_apply": "Apply preventatively before rain spells or at initial appearance of bacterial or fungal leaf spots.",
        "phi_days": "7 to 10 days.",
        "toxicity_level": "Blue Triangle (Moderately Toxic).",
        "safety_ppe": "Protective eyewear and rubber gloves.",
        "tank_mix_cautions": "Do NOT mix with acidic substances, lime sulphur, dithiocarbamates, or organophosphates."
    },
    "profenofos_cypermethrin": {
        "chemical_name": "Profenofos 40% + Cypermethrin 4% EC",
        "popular_brands": ["Roket", "Profer", "Polytrin C", "Nagpraj"],
        "classification": "Combination Organophosphate + Synthetic Pyrethroid Insecticide",
        "mode_of_action": "Contact, stomach, and ovicidal action with rapid knockdown and translaminar penetration.",
        "approved_crops": "Cotton, Paddy, Vegetables, Soybean, Pulses.",
        "target_pests": "Bollworms, Spodoptera (Tobacco Caterpillar), Aphids, Jassids, Whiteflies, Thrips, Stem Borers.",
        "dosage_foliar": "2.0 ml per liter of water (400 ml per acre in 200 liters of water).",
        "dosage_soil": "Foliar application only.",
        "when_to_apply": "At peak caterpillar hatching or severe sucking pest infestation.",
        "phi_days": "15 days for cotton, 7 days for vegetables.",
        "toxicity_level": "Yellow Triangle (Highly Toxic).",
        "safety_ppe": "Strict PPE: Full mask, apron, and rubber gloves.",
        "tank_mix_cautions": "Compatible with most neutral fungicides."
    },
    "urea_fertilizer": {
        "chemical_name": "Urea (46% Nitrogen)",
        "popular_brands": ["IFFCO Urea", "KRIBHCO", "NFL", "Chambal", "Coromandel"],
        "classification": "Primary Nitrogenous Solid / Foliar Fertilizer",
        "mode_of_action": "Provides readily available nitrogen for vegetative growth, chlorophyll synthesis, and protein formation.",
        "approved_crops": "All field crops, cereals (Paddy, Wheat, Maize), vegetables, fruits, and commercial crops.",
        "target_pests": "Corrects Nitrogen Deficiency (stunted growth, pale yellow lower leaves).",
        "dosage_foliar": "Foliar spray: 15 g to 20 g per liter of water (1.5% to 2.0% spray solution). Soil application: 30–50 kg/acre in split doses.",
        "dosage_soil": "Basal or top dressing as per soil test recommendations.",
        "when_to_apply": "Top dress at active tillering, vegetative surge, or early flowering. Avoid applying immediately before heavy rain or during waterlogging.",
        "phi_days": "None (Nutrient).",
        "toxicity_level": "Green (Non-hazardous fertilizer).",
        "safety_ppe": "Wash hands after handling.",
        "tank_mix_cautions": "Compatible with most pesticide sprays at 1–2% foliar concentration. Nano Urea @ 2–4 ml/L."
    },
    "dap_fertilizer": {
        "chemical_name": "Di-Ammonium Phosphate (DAP 18:46:0)",
        "popular_brands": ["IFFCO DAP", "KRIBHCO DAP", "Coromandel Gromor", "Paradeep"],
        "classification": "Phosphatic & Nitrogenous Complex Fertilizer",
        "mode_of_action": "Supplies 18% Ammoniacal Nitrogen and 46% Water Soluble Phosphate for vigorous root elongation and seedling establishment.",
        "approved_crops": "All field crops, pulses, oilseeds, wheat, paddy, cotton, vegetables.",
        "target_pests": "Corrects Phosphorus deficiency (purplish leaf discoloration, poor root architecture, delayed maturity).",
        "dosage_foliar": "Typically soil-applied (40–50 kg per acre as basal dose). For foliar: use 19:19:19 or 0:52:34 @ 5 g/L.",
        "dosage_soil": "Place 4–5 cm below and to the side of seeds at sowing time.",
        "when_to_apply": "At sowing or transplanting as basal application.",
        "phi_days": "None.",
        "toxicity_level": "Green (Fertilizer).",
        "safety_ppe": "Standard handling precautions.",
        "tank_mix_cautions": "Do not mix with zinc sulphate or calcium fertilizers in the same solution to prevent precipitation."
    },
    "fipronil": {
        "chemical_name": "Fipronil (Approved CIBRC/PPQS Formulations: 0.3% GR Granules & 5% SC Liquid)",
        "popular_brands": ["SHRIRAM FIPRO", "Regent", "Prince", "Mortar", "Mahaveer", "FX-50", "Fipro"],
        "classification": "Broad-Spectrum Phenylpyrazole Insecticide (GABA Receptor Antagonist)",
        "mode_of_action": "Systemic and contact action. Ingested or absorbed by roots/foliage, blocking neural chloride channels.",
        "approved_crops": "Paddy (Rice), Sugarcane, Cotton, Chilli, Cabbage, Wheat, Onion.",
        "target_pests": "Yellow Stem Borer, Leaf Folder, Gall Midge, Brown Plant Hopper (BPH), Early Shoot Borer, Root Borer, Termites, Thrips, Aphids.",
        "dosage_foliar": "FOR LIQUID 5% SC: 1.5 to 2.0 ml per liter of water (400 to 500 ml per acre dissolved in 200 liters of water) as foliar spray.",
        "dosage_soil": "FOR GRANULES 0.3% GR: 7.5 to 10 kg per acre (17 to 25 kg/ha) broadcast evenly in standing water (2–3 cm) in paddy or mixed in furrows in sugarcane. ⚠️ CRITICAL: NEVER dissolve granules in a spray pump/tank!",
        "when_to_apply": "Paddy: Apply 0.3% GR at 15–25 days after transplanting (DAT) for stem borer and leaf folder. Keep standing water for 48–72 hours. Spray 5% SC at appearance of thrips/borers.",
        "phi_days": "32 days for paddy (rice), 7 days for chilli and cabbage.",
        "toxicity_level": "Blue Triangle (Moderately Toxic). Toxic to aquatic life and honeybees.",
        "safety_ppe": "Wear rubber gloves, boots, and face mask. Do not release standing treated water into fish ponds for 7 days.",
        "tank_mix_cautions": "Compatible with common neutral fungicides (Mancozeb, Carbendazim, Saaf). Do not mix with strong alkaline solutions."
    },
    "lambda_cyhalothrin": {
        "chemical_name": "Lambda-Cyhalothrin 5% EC / 4.9% CS",
        "popular_brands": ["Karate", "Matador", "Kung Fu", "Reeva", "Silfen"],
        "classification": "Synthetic Pyrethroid Insecticide",
        "mode_of_action": "Non-systemic contact and stomach action with rapid knockdown and long residual repellent activity.",
        "approved_crops": "Cotton, Paddy, Tomato, Brinjal, Chilli, Okra, Onion, Groundnut, Mango.",
        "target_pests": "Bollworms, Stem Borer, Leaf Folder, Gall Midge, Thrips, Flea Beetle, Fruit Borer, Shoot Borer.",
        "dosage_foliar": "1.0 ml to 1.5 ml per liter of water (200 to 300 ml per acre in 200 liters of water).",
        "dosage_soil": "Foliar spray only.",
        "when_to_apply": "Apply at early infestation of caterpillars, borers, or thrips.",
        "phi_days": "15 days for cotton, 14 days for paddy, 5 days for tomato and chilli.",
        "toxicity_level": "Yellow Triangle (Highly Toxic).",
        "safety_ppe": "Protective eyewear, rubber gloves, and respirator mask.",
        "tank_mix_cautions": "Compatible with most standard fungicides."
    },
    "spinosad": {
        "chemical_name": "Spinosad 45% SC",
        "popular_brands": ["Tracer", "Spintor", "Success"],
        "classification": "Naturalyte Bio-Insecticide (Fermentation derived)",
        "mode_of_action": "Translaminar and contact activity. Binds nicotinic acetylcholine receptors, disrupting neural transmission.",
        "approved_crops": "Cotton, Chilli, Redgram, Tomato, Brinjal, Cabbage.",
        "target_pests": "American Bollworm, Spotted Bollworm, Thrips, Fruit Borer, Diamondback Moth (DBM), Pod Borer.",
        "dosage_foliar": "0.3 ml to 0.4 ml per liter of water (60 to 75 ml per acre in 200 liters of water).",
        "dosage_soil": "Foliar application only.",
        "when_to_apply": "At pest emergence; highly effective for IPM and thrips resistance management.",
        "phi_days": "3 days for vegetables, 14 days for cotton.",
        "toxicity_level": "Blue Triangle (Moderately Toxic). Safe for beneficial insects after spray dries.",
        "safety_ppe": "Standard protective mask and gloves.",
        "tank_mix_cautions": "Compatible with most neutral fungicides."
    },
    "propiconazole": {
        "chemical_name": "Propiconazole 25% EC",
        "popular_brands": ["Tilt", "Radar", "Bumper", "Result"],
        "classification": "Broad-Spectrum Systemic Triazole Fungicide",
        "mode_of_action": "Systemic with protective and curative action. Demethylation inhibitor (DMI) of sterol biosynthesis.",
        "approved_crops": "Wheat, Paddy, Groundnut, Tea, Soybean, Coffee.",
        "target_pests": "Karnal Bunt, Rust (Yellow/Brown/Black), Sheath Blight, Tikka Disease, Blister Blight.",
        "dosage_foliar": "1.0 ml per liter of water (200 ml per acre in 200 liters of water).",
        "dosage_soil": "Foliar application.",
        "when_to_apply": "Apply at boot leaf stage for wheat or early sheath blight detection in paddy.",
        "phi_days": "30 days for wheat and paddy.",
        "toxicity_level": "Blue Triangle (Moderately Toxic).",
        "safety_ppe": "Wear rubber gloves and mask.",
        "tank_mix_cautions": "Compatible with most neutral insecticides."
    },
    "tebuconazole": {
        "chemical_name": "Tebuconazole 25.9% EC / 10% + Sulphur 65% WG",
        "popular_brands": ["Folicur", "Harsh", "Orius", "Custodia (in mix)"],
        "classification": "Broad-Spectrum Systemic Triazole Fungicide",
        "mode_of_action": "Ergosterol biosynthesis inhibitor. Translocated systemically within plant tissues.",
        "approved_crops": "Chilli, Groundnut, Paddy, Onion, Soybean, Tomato.",
        "target_pests": "Fruit Rot / Anthracnose, Powdery Mildew, Tikka Leaf Spot, Blast, Purple Blotch.",
        "dosage_foliar": "1.0 ml to 1.5 ml per liter of water (250–300 ml per acre in 200 liters of water).",
        "dosage_soil": "Foliar application.",
        "when_to_apply": "Spray at first sign of disease onset; repeat after 10–14 days if humid conditions persist.",
        "phi_days": "15 to 21 days.",
        "toxicity_level": "Blue Triangle (Moderately Toxic).",
        "safety_ppe": "Protective gloves and goggles.",
        "tank_mix_cautions": "Compatible with most insecticides."
    },
    "cartap_hydrochloride": {
        "chemical_name": "Cartap Hydrochloride 4% GR / 50% SP",
        "popular_brands": ["Padan", "Caldan", "Kritap", "Sanvex"],
        "classification": "Nereistoxin Analogue Insecticide",
        "mode_of_action": "Systemic, contact, and stomach poison. Blocks cholinergic synaptic transmissions in insect central nervous system.",
        "approved_crops": "Paddy (Rice), Sugarcane.",
        "target_pests": "Stem Borer, Leaf Folder, Whorl Maggot, Early Shoot Borer, Top Borer.",
        "dosage_foliar": "Foliar (50% SP): 1.5 g to 2.0 g per liter of water (400 g per acre in 200L water).",
        "dosage_soil": "Granules (4% GR): 7.5 kg to 10 kg per acre broadcast into 2–3 cm standing water.",
        "when_to_apply": "Apply at 20–30 days after transplanting (DAT) or at initial moth flight.",
        "phi_days": "21 days for paddy.",
        "toxicity_level": "Yellow Triangle (Highly Toxic).",
        "safety_ppe": "Strict protective clothing, rubber gloves, and respirator.",
        "tank_mix_cautions": "Do not mix with alkaline substances or copper fungicides."
    },
    "pendimethalin": {
        "chemical_name": "Pendimethalin 30% EC / 38.7% CS",
        "popular_brands": ["Stomp", "Dhanutop", "Dost", "Panida"],
        "classification": "Selective Dinitroaniline Pre-Emergence Herbicide",
        "mode_of_action": "Inhibits microtubule assembly, preventing cell division and elongation during weed seed germination.",
        "approved_crops": "Soybean, Cotton, Wheat, Paddy, Onion, Groundnut, Mustard, Pulses.",
        "target_pests": "Annual grasses (Echinochloa, Digitaria, Phalaris minor) and broadleaf weeds (Amaranthus, Chenopodium, Portulaca).",
        "dosage_foliar": "Pre-emergence soil spray: 3.0 ml to 4.0 ml per liter of water (1.0 to 1.3 liters per acre in 200–250 liters of water).",
        "dosage_soil": "Spray uniformly on well-prepared moist soil surface within 24–48 hours after sowing.",
        "when_to_apply": "Pre-emergence only (before weed seeds germinate). Requires adequate soil moisture.",
        "phi_days": "Pre-emergence; no residue at crop harvest.",
        "toxicity_level": "Blue Triangle (Moderately Toxic).",
        "safety_ppe": "Rubber gloves, goggles, and protective clothing. Use flat fan or floodjet nozzle.",
        "tank_mix_cautions": "Do not disturb the soil layer after spraying."
    },
    "azadirachtin_neem": {
        "chemical_name": "Azadirachtin 0.15% (1500 ppm) / 1% (10,000 ppm) EC",
        "popular_brands": ["Neemazal", "Nimbecidine", "Econeem", "Bioneem", "Neem Gold"],
        "classification": "Botanical Bio-Pesticide & Antifeedant",
        "mode_of_action": "Multiple modes: antifeedant, repellent, oviposition deterrent, and insect growth regulator (IGR) disrupting ecdysone.",
        "approved_crops": "All crops, vegetables, fruits, pulses, cereals, organic farming.",
        "target_pests": "Whiteflies, Aphids, Jassids, Thrips, Caterpillars, Leaf Miners, Mites.",
        "dosage_foliar": "1500 ppm: 4.0 ml to 5.0 ml per liter of water. 10,000 ppm: 1.5 ml to 2.0 ml per liter of water (with 1 ml/L liquid soap).",
        "dosage_soil": "Neem cake @ 100–150 kg/acre for root nematodes and grubs.",
        "when_to_apply": "Preventive or early vegetative stage. Spray during late afternoon or evening.",
        "phi_days": "Zero to 1 day (Eco-friendly, residue free).",
        "toxicity_level": "Green Triangle (Eco-Friendly / Non-toxic to humans).",
        "safety_ppe": "Standard handling.",
        "tank_mix_cautions": "Compatible with most biological agents (Trichoderma, Beauveria) and chemical insecticides."
    }
}

def find_agrochemical_in_db(query_str: str) -> Optional[Dict[str, Any]]:
    """
    Finds matching CIBRC agrochemical intelligence from the local curated database
    by searching across active ingredients, chemical names, and popular brand names.
    Supports robust multi-word token matching and fuzzy substring search.
    """
    if not query_str or not query_str.strip():
        return None

    cleaned = query_str.strip().lower()
    cleaned_words = set(re.findall(r"[a-z0-9]+", cleaned))

    # 1. Exact or partial key match
    for key, data in AGROCHEMICAL_DATABASE.items():
        if key in cleaned:
            return data
        key_parts = key.split("_")
        if all(part in cleaned_words for part in key_parts):
            return data

    # 2. Match brand names (e.g. "SHRIRAM FIPRO", "Regent", "Coragen", "Saaf")
    for key, data in AGROCHEMICAL_DATABASE.items():
        for brand in data.get("popular_brands", []):
            b_lower = brand.lower()
            if b_lower in cleaned or cleaned in b_lower:
                return data
            # Check individual significant brand tokens (e.g. "fipro", "coragen", "confidor")
            b_tokens = [w for w in re.findall(r"[a-z0-9]+", b_lower) if len(w) > 3 and w not in {"plus", "super", "gold", "dual", "farm", "solutions"}]
            for bt in b_tokens:
                if bt in cleaned_words or any(bt in cw for cw in cleaned_words):
                    return data

    # 3. Match active ingredients and chemical tokens
    for key, data in AGROCHEMICAL_DATABASE.items():
        chem = data.get("chemical_name", "").lower()
        chem_tokens = [t for t in re.findall(r"[a-z]+", chem) if len(t) > 4 and t not in {"water", "soluble", "granule", "liquid", "powder", "action"}]
        for ct in chem_tokens:
            if ct in cleaned_words or any(ct in cw for cw in cleaned_words):
                return data

    return None

def format_cibrc_dossier(match: Dict[str, Any], query_details: str = "") -> str:
    """
    Formats verified government registration data (CIBRC / PPQS, Ministry of Agriculture)
    into a crisp, authoritative briefing for advisory synthesis.
    """
    if not match:
        return ""

    lines = [
        "OFFICIAL GOVERNMENT DATA (Source: Central Insecticides Board & Registration Committee - CIBRC / PPQS, Ministry of Agriculture, Govt of India):",
        f"- Registered Formulation & Active: {match.get('chemical_name', 'N/A')}",
        f"- Chemical Classification: {match.get('classification', 'N/A')}",
        f"- Approved Major Crops: {match.get('approved_crops', 'N/A')}",
        f"- Registered Target Pests & Diseases: {match.get('target_pests', 'N/A')}",
        f"- Official Foliar / Spray Dilution & Dosage: {match.get('dosage_foliar', 'N/A')}",
        f"- Official Soil / Granules / Drench Dosage: {match.get('dosage_soil', 'N/A')}",
        f"- Recommended Application Timing: {match.get('when_to_apply', 'N/A')}",
        f"- Official Pre-Harvest Interval (PHI Waiting Period): {match.get('phi_days', 'N/A')}",
        f"- Toxicity Level: {match.get('toxicity_level', 'N/A')}",
        f"- Safety & PPE: {match.get('safety_ppe', 'N/A')}",
        f"- Tank Mix Cautions: {match.get('tank_mix_cautions', 'N/A')}"
    ]
    return "\n".join(lines)

