import os

from flask_cors import CORS

from app import create_app

app = create_app()

CORS(
    app,
    origins=[
        "http://localhost:5173",           # local development
        "https://library-management-front-end-ten.vercel.app"  # production
    ]
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)