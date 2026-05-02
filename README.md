# Team Artwork App

Full-stack application for validating team logos, scraping player data, processing assets, and generating fallback artwork.

## Stack

- Backend: FastAPI
- Frontend: React + Vite
- Image processing: Pillow, OpenCV
- Similarity: CLIP
- Scraping: requests + BeautifulSoup

## Main Endpoint

`POST /process-team`

Form data:

- `team_name`: required string
- `logo`: optional image file

Response:

```json
{
  "validation": {
    "team": "Example Team",
    "confidence": 0.82,
    "status": "valid",
    "matched_sources": ["https://example.com/logo.png"],
    "color_match": 0.77,
    "visual_match": 0.84
  },
  "players": [
    {
      "name": "Player Name",
      "role": "Forward",
      "image_url": null,
      "processed_image_path": "/static/headshots/player-name.png"
    }
  ],
  "artwork": {
    "thumbnail": "/static/artwork/example-team-thumbnail.png",
    "poster": "/static/artwork/example-team-poster.png",
    "variants": []
  }
}
```

## Run

### Backend

If you're out of tokens or deploying, it's recommended to run the backend in a virtual environment:

```bash
cd backend
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the backend
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```
