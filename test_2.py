import requests

with open("test_claim.pdf", "rb") as f:
    response = requests.post("http://localhost:8000/modifier-check", files={"file": f})

print(response.status_code)
print(response.json())
