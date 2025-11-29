# PDF Metadata Extractor

Automatically extract bibliographic metadata from research paper PDFs using Google Gemini AI.

## Features

- 📄 Extracts metadata from PDF research papers
- 🤖 Uses Google Gemini 2.5 Flash AI model
- 📊 Exports results to JSON
- 🔄 Incremental processing (resumes where you left off)
- 🎯 Extracts: Title, Authors, Year, Journal, DOI, Keywords, Abstract

## Installation

### 1. Install Dependencies

```bash
pip install google-genai PyPDF2 python-dotenv
```

### 2. Set Up API Key

Create a `.env` file:

```bash
GEMINI_API_KEY=your-api-key-here
```

Get your free API key: https://aistudio.google.com/app/apikey

## Usage

### Basic Usage

```bash
python3 extract_metadata.py
```

When prompted, enter the path to your PDF folder (e.g., `pdf` or `/path/to/pdfs`).

### Test the API

```bash
python3 test_gemini.py
```

## Output

The script creates two files:

1. **`metadata.json`** - Contains all extracted metadata
2. **`processed_files.json`** - Tracks which files have been processed

### Example Output

```json
{
  "title": "Machine Learning in Healthcare",
  "authors": ["John Doe", "Jane Smith"],
  "year": "2024",
  "journal": "AI in Medicine",
  "doi": "10.1234/example",
  "keywords": ["machine learning", "healthcare", "AI"],
  "abstract": "This paper explores...",
  "filename": "paper.pdf",
  "relative_path": "papers/paper.pdf"
}
```

## How It Works

1. **Extracts text** from first 3 pages of each PDF (using PyPDF2)
2. **Sends text** to Google Gemini AI
3. **Parses response** as JSON metadata
4. **Saves results** incrementally (survives interruptions)

## Features

- ✅ Processes PDFs recursively in subdirectories
- ✅ Skips already processed files
- ✅ Resume capability if interrupted
- ✅ Automatic retry on API errors
- ✅ Debug output for troubleshooting

## Commands

**Reset and start fresh:**
```bash
rm processed_files.json metadata.json
python3 extract_metadata.py
```

**View results:**
```bash
cat metadata.json | python3 -m json.tool
```

## Requirements

- Python 3.7+
- Google Gemini API key (free tier available)
- PDF files with text (not scanned images)

## Troubleshooting

**"No text extracted from PDF"**
- PDF might be scanned images (needs OCR)
- Try opening the PDF and checking if text is selectable

**"Quota exceeded"**
- Using free tier model: `gemini-2.5-flash`
- Wait for quota to reset (see error message for time)

**"API key not found"**
- Check `.env` file exists in the same directory
- Verify `GEMINI_API_KEY=your-key` is correct

## License

MIT

## Author

Created with Google Gemini AI
