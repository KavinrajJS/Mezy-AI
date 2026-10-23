# Mezy — AI-Powered Customer Review Intelligence

**Understand Your Customers. Improve Your Business.**

Mezy helps restaurant and cafe owners turn customer reviews into meaningful business insights. It analyses customer feedback to highlight sentiment, recurring topics, and opportunities to improve the customer experience.

## Features

- **Review Upload:** Upload reviews using a CSV file or paste customer feedback directly into the application.
- **AI-Powered Analysis:** Use the Gemini API to analyse customer sentiment, identify recurring topics, and generate insights.
- **Overview Dashboard:** Explore review statistics, trends, and visual summaries through interactive charts.
- **Review Analysis:** Examine individual reviews and understand customer feedback in greater detail.
- **Action Tracker:** Record improvement actions, set priorities, and track progress using SQLite.
- **Report Export:** Generate PDF business reports, editable Word documents, and CSV files.
- **Report Language Options:** Select from the available language options when generating reports.

## Technology Stack

| Component | Technology |
|---|---|
| User Interface | Streamlit |
| AI Analysis | Gemini API (`google-genai`) |
| Data Processing | Pandas |
| Data Visualisation | Plotly |
| Database | SQLite (`sqlite3`) |
| PDF Generation | ReportLab |
| Word Documents | `python-docx` |
| Environment Configuration | `python-dotenv` |
| Programming Language | Python |

## Project Structure

```text
Mezy-AI/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── .streamlit/
│   └── config.toml
├── assets/
│   ├── styles.css
│   └── application images and logos
├── components/
│   ├── __init__.py
│   ├── action_tracker.py
│   ├── dashboard.py
│   ├── loading_animation.py
│   ├── review_table.py
│   ├── sidebar.py
│   ├── topic_explorer.py
│   └── upload.py
├── config/
│   ├── __init__.py
│   └── settings.py
├── data/
│   ├── README.md
│   └── sample_reviews.csv
├── src/
│   ├── __init__.py
│   ├── analytics.py
│   ├── data_cleaning.py
│   ├── database.py
│   ├── gemini_service.py
│   ├── report_generator.py
│   ├── review_analysis.py
│   └── translations.py
└── tests/
    ├── test_action_tracker_ui.py
    ├── test_analytics.py
    ├── test_data_cleaning.py
    ├── test_database.py
    ├── test_insights.py
    ├── test_multilingual.py
    ├── test_report_generator.py
    ├── test_review_analysis.py
    ├── test_ui_analysis_state.py
    └── test_variations_runner.py
```

## Getting Started

### Prerequisites

- Python 3.10 or a compatible version supported by the dependencies
- Git
- A Gemini API key

### 1. Clone the Repository

```bash
git clone https://github.com/KavinrajJS/Mezy-AI.git
cd Mezy-AI
```

### 2. Create a Virtual Environment

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure the Gemini API Key

Create a local `.env` file from the provided `.env.example` file.

**Windows (PowerShell):**

```powershell
Copy-Item .env.example .env
```

**macOS / Linux:**

```bash
cp .env.example .env
```

Open `.env` and add your Gemini API key:

```env
GEMINI_API_KEY=your_actual_api_key_here
```

### 5. Run the Application

```bash
python -m streamlit run app.py
```

Once the application starts, open the local URL displayed in your terminal. The default address is usually http://localhost:8501.

## Sample Data

Mezy includes `data/sample_reviews.csv`, which contains sample customer reviews in English.

You can use this dataset to explore the application's dashboard and review analysis features without preparing your own CSV file.

## Notes

- AI-generated insights are intended to help users understand customer feedback and identify potential areas for improvement.
- Analysis results may vary depending on the content and context of the reviews.
- Gemini API usage is subject to the applicable service quotas and rate limits.
- PDF and Word report formatting may vary depending on font availability and document settings.

