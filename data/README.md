# data/

This folder holds sample review data used during development.

## Files

| File | Purpose |
|------|---------|
| `sample_reviews.csv` | 30 fictional restaurant reviews mixing English, Tamil, and Tanglish |

## Expected CSV format

Your own review CSV should contain these columns:

| Column | Required | Description |
|--------|----------|-------------|
| `review_text` | **Yes** | The customer's written review |
| `rating` | No | Numeric rating (e.g. 1–5) |
| `review_date` | No | Date the review was posted (any standard format) |
| `source` | No | Platform the review came from (e.g. Google, Zomato) |

## Important

- Do **not** upload real customer data to a shared or public environment.
- The `mezy.db` SQLite file is created at runtime and must **not** be committed to Git.
- Generated report files (`.pdf`, `.docx`, `.csv`) are excluded by `.gitignore`.
