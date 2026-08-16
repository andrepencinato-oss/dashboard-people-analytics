import requests

def test_login():
    url = "http://127.0.0.1:5009/api/login"
    payload = {
        "username": "andre",
        "password": "*Savoia10"
    }
    try:
        response = requests.post(url, json=payload)
        print("Status Code:", response.status_code)
        print("Response:", response.json())
    except Exception as e:
        print("Failed:", e)

if __name__ == "__main__":
    test_login()
