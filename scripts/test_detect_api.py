import requests


API_URL = "http://127.0.0.1:5000/api/detect"


test_images = [
    {
        "image_path": "test_images/road1.png",
        "report_id": 1
    },
    {
        "image_path": "test_images/good.png",
        "report_id": 2
    }
]


for payload in test_images:
    print("=" * 50)
    print("Testing:", payload["image_path"])

    response = requests.post(API_URL, json=payload)

    print("Status code:", response.status_code)

    try:
        print("Response:", response.json())
    except Exception:
        print("Raw response:", response.text)