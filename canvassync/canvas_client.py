import requests

from canvassync.config import CANVAS_BASE_URL, CANVAS_TOKEN


def test_connection():
    response = requests.get(
        f"{CANVAS_BASE_URL}/api/v1/users/self",
        headers={
            "Authorization": f"Bearer {CANVAS_TOKEN}",
        },
        timeout=10,
    )

    response.raise_for_status()
    user = response.json()

    print(f"Connected to Canvas as: {user['name']}")


if __name__ == "__main__":
    test_connection()