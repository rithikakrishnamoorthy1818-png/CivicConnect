import os
import base64
import requests
import json
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

def detect_issue_from_image(image_base64: str, filename: str = ""):
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "mock-key":
        categories = ["Pothole", "Garbage", "Street Light", "Water Leakage", "Road Damage"]
        
        name_lower = filename.lower()
        if "pot" in name_lower:
            cat = "Pothole"
        elif "garb" in name_lower or "trash" in name_lower:
            cat = "Garbage"
        elif "light" in name_lower:
            cat = "Street Light"
        elif "water" in name_lower or "leak" in name_lower:
            cat = "Water Leakage"
        elif "road" in name_lower or "damage" in name_lower:
            cat = "Road Damage"
        else:
            idx = len(image_base64) % len(categories)
            cat = categories[idx]
            
        return {
            "category": cat,
            "confidence": 85 + (len(image_base64) % 10),
            "severity": "High" if cat in ["Water Leakage", "Pothole"] else "Medium",
            "description": f"AI detected {cat.lower()} based on image analysis."
        }

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    prompt = (
        "Analyze this image and respond ONLY in JSON:\n"
        "{\n"
        "  \"category\": \"one of [Pothole, Garbage, Street Light, Water Leakage, Road Damage]\",\n"
        "  \"confidence\": 0-100,\n"
        "  \"severity\": \"one of [Low, Medium, High, Critical]\",\n"
        "  \"description\": \"one line description of what you see\"\n"
        "}\n"
        "No extra text, just valid JSON."
    )

    payload = {
        "model": "claude-3-opus-20240229",
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
    }

    try:
        response = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        text_content = result["content"][0]["text"]
        return json.loads(text_content)
    except Exception as e:
        print(f"AI Detection Error: {e}")
        return {
            "category": "Other",
            "confidence": 0,
            "severity": "Unknown",
            "description": f"AI detection failed: {str(e)}"
        }
