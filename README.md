# Mezy — AI-Powered Customer Review Intelligence

> **Tagline:** Understand Your Customers. Improve Your Business.

Mezy is a portfolio-grade AI application that helps restaurant and café owners turn raw customer reviews into clear, actionable business insights — without reading hundreds of reviews manually.

---

## Features

- **Upload reviews** via CSV or paste directly.
- **Gemini-powered analysis** — sentiment, topics, and aspect-level insights.
- **Interactive dashboard** — charts, filters, and evidence-backed findings.
- **Topic Explorer** — drill down into Food Quality, Delivery, Staff, and more.
- **Action Tracker** — save improvement actions with priority and status (SQLite).
- **Multilingual support** — English, Tamil, and Tanglish input; output in any of the three.
- **Export** — PDF business report, editable Word document, or CSV.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| UI | Streamlit |
| AI | Gemini API (`google-genai`) |
| Data | Pandas |
| Charts | Plotly |
| Storage | SQLite (`sqlite3`) |
| PDF | ReportLab |
| Word | python-docx |
| Config | python-dotenv |

---

## Project Structure

```
Mezy-AI/
├── app.py                  # Entry point
├── requirements.txt
├── .env.example            # Copy to .env and add your API key
├── config/settings.py      # All constants and paths
├── src/                    # Business logic
│   ├── data_cleaning.py
│   ├── gemini_service.py
│   ├── review_analysis.py
│   ├── insights.py
│   ├── database.py
│   ├── report_generator.py
│   └── translations.py
├── components/             # Streamlit UI components
│   ├── sidebar.py
│   ├── upload.py
│   ├── dashboard.py
│   ├── review_table.py
│   ├── topic_explorer.py
│   ├── action_tracker.py
│   └── loading_animation.py
├── assets/                 # CSS and images
├── data/sample_reviews.csv # 30 fictional reviews for testing
└── tests/                  # Automated tests
```

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-username/Mezy-AI.git
cd Mezy-AI
```

### 2. Create and activate the virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the API key

```bash
copy .env.example .env   # Windows
# OR
cp .env.example .env     # macOS / Linux
```

Open `.env` and replace `your_actual_api_key_here` with your Gemini API key.

> **Never commit your `.env` file.** It is excluded by `.gitignore`.

### 5. Run the application

```bash
streamlit run app.py
```

The application opens at `http://localhost:8501`.

---

## Sample Data

A fictional 30-review dataset is provided in `data/sample_reviews.csv`.  
It includes English, Tamil, and Tanglish reviews with varied sentiments.

Click **Use Sample Data** on the home screen to load it without uploading a file.

---

## Limitations

- Tanglish interpretation accuracy depends on context; some reviews may be classified as Uncertain.
- The Gemini free tier has usage limits; large datasets may be processed in batches.
- Tamil PDF rendering requires a compatible Unicode font (configured in Milestone 6).
- This is a college portfolio project, not a production system.

---

## Development Milestones

| Milestone | Status | Description |
|-----------|--------|-------------|
| 1 | ✅ Complete | Foundation, folder structure, UI shell |
| 2 | 🔜 Next | CSV upload, validation, data cleaning |
| 3 | 🔜 | Gemini integration, structured analysis |
| 4 | 🔜 | Analytics dashboard with charts |
| 5 | 🔜 | Loading animation, multilingual output |
| 6 | 🔜 | Action tracker, SQLite, exports |
| 7 | 🔜 | Testing, polish, portfolio preparation |

---

## License

This project is for educational and portfolio purposes.
