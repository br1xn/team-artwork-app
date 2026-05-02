# Team Artwork Application: Project Context & Workflow

This document serves as a high-level overview of the Team Artwork Application. It chronicles the evolution of our application based on our past conversations and details the technical workflow from start to finish. This ensures you have a reliable reference point for the application's architecture and rationale.

## Project Context & Evolution

Over the course of our development sessions, the Proof of Concept has evolved into a robust, fallback-driven application designed to automatically generate premium sports media assets for teams across major leagues (such as the NFL and IPL).

**Key Iterations:**
1. **Initial Proof of Concept:** We started with basic web scraping and a standard PIL-based template generation for artworks.
2. **AI Integration ("Nano Banana"):** We integrated AI image generation (initially via Google Gemini / "Nano Banana" image generation) to move away from generic templates and produce dynamic, high-budget broadcast graphics.
3. **Robust Fallbacks & Edge Cases:** Added support for robust data scraping (switching from brittle HTML parsing to the official ESPN API for high-resolution NFL player headshots) and integrated `Pollinations.ai` utilizing the `Flux` model. This allows us to keep generating premium art even in a zero-credit or API key-less environment.
4. **Validation Transparency:** Implemented HuggingFace Transformers (CLIP model) to score logos against scraped candidate logos based on visual and color similarity, exposing this directly to the UI to ensure users know exactly *why* their team logo was verified.

---

## Application Workflow

When a user submits a request for a team (e.g., "Baltimore Ravens" or "Chennai Super Kings"), the backend triggers a pipeline consisting of three primary steps:

### 1. Logo Validation (`LogoValidator`)
The goal is to ensure the uploaded logo truly belongs to the requested team.
- **Sourcing:** The backend searches Wikipedia, Google Images, and Official Team Websites to find candidate logos.
- **Verification:** It uses the `openai/clip-vit-base-patch32` Vision-Language model to encode the user's logo and compare its visual embeddings with the online candidates.
- **Color Matching:** OpenCV applies K-Means clustering to verify the dominant colors align.
- **Transparency:** The backend computes a confidence score and generates a `validation_evidence` statement, informing the frontend exactly which model was used and how many sources verified it.

### 2. Roster Scraping (`PlayerScraper`)
The application requires player headshots to make the artwork dynamic.
- **League Detection:** The system detects if the team is an NFL franchise or an IPL team based on internal mappings.
- **ESPN / Official API:** It reaches out to APIs (like ESPN for the NFL) or parses official league websites (like IPLT20.com) to fetch pristine, high-resolution headshots without relying entirely on Wikipedia's text-only tables.
- **Image Processing:** Fetched images are passed to the `ImageProcessor` to convert them into standardized transparent assets, perfect for overlays.

### 3. Artwork Generation & Composition (`ArtworkGeneratorService`)
This is the core pipeline where the media is created.
- **Asset Generation:** The backend requests a high-budget, cinematic sports background without any distorted text. It targets Google Gemini APIs first. If credits are exhausted, it instantly fails over to **Pollinations.ai (Flux Model)** to generate hyper-realistic assets for free.
- **Aspect Ratios:** Two distinct formats are generated:
  - **Poster:** 4:3 Aspect Ratio (1600x1200)
  - **Thumbnail:** 16:9 Aspect Ratio (1920x1080)
- **Dynamic Overlays:** Once the AI base is ready, the `Pillow` library takes over. It applies a sleek dark gradient at the bottom, stamps the official team logo with an aesthetic circular plate, draws the scraped player headshots inside dynamic, color-tinted rings, and prints the team's name using their dominant colors.

---

## Key Highlights
- **Zero-Credit Tolerance:** Through `Pollinations.ai`, you don't need a massive budget to keep generating beautiful base posters.
- **Security & Stability:** Sensitive API keys are managed safely inside `.env` files. The API routes are strictly rate-limited using `slowapi` (5 requests per minute) to prevent server overload.
- **Live Deployment Ready:** The backend runs via `uvicorn` and FastAPI, and the Vite-React frontend can be built efficiently for production.

*End of Workflow Documentation.*
