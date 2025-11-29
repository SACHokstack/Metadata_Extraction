import os
import json
import time
from typing import Dict, Optional, Set
import PyPDF2
from google import genai
from google.genai import types
from pathlib import Path

# Try to load from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Note: python-dotenv not installed. Install it with 'pip install python-dotenv' to use .env files")

# Use Gemini API key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

class PaperProcessor:
    def __init__(self, gemini_api_key: str):
        """Initialize the paper processor with Gemini API credentials."""
        # Set API key as environment variable for the new Google Gemini SDK
        os.environ['GEMINI_API_KEY'] = gemini_api_key

        # Initialize the Gemini client
        self.client = genai.Client(api_key=gemini_api_key)

        # Using Gemini 3 Pro Preview
        self.model_name = 'gemini-2.5-flash'
        print(f"Initialized with model: {self.model_name}")
        
        self.processed_files_path = 'processed_files.json'
        self.metadata_path = 'metadata.json'
        
        self.system_prompt = """You are a research paper metadata extractor. Given text from the first few pages of a paper, extract the following information:
- Title
- Authors (as a list)
- Year
- Journal/Conference
- DOI (if available)
- Keywords (if available)
- Abstract (the full abstract text if found)

If any field is unreadable or not found, return "unknown" for that field.

Return ONLY a raw JSON object with these exact field names: title, authors, year, journal, doi, keywords, abstract. Do not include any other text or markdown formatting."""

    def load_processed_files(self) -> Set[str]:
        """Load the set of already processed files."""
        if os.path.exists(self.processed_files_path):
            try:
                with open(self.processed_files_path, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
            except (json.JSONDecodeError, IOError):
                print(f"Warning: Could not load {self.processed_files_path}. Starting fresh.")
                return set()
        return set()

    def save_processed_file(self, filename: str) -> None:
        """Add a filename to the processed files list."""
        processed_files = self.load_processed_files()
        processed_files.add(filename)
        
        with open(self.processed_files_path, 'w', encoding='utf-8') as f:
            json.dump(list(processed_files), f, indent=2)

    def load_existing_metadata(self) -> list:
        """Load existing metadata if available."""
        if os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                print(f"Warning: Could not load {self.metadata_path}. Starting fresh.")
                return []
        return []

    def extract_text_from_pdf(self, pdf_path: str, max_pages: int = 3) -> str:
        """Extract text from the first few pages of a PDF file."""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                num_pages = min(len(pdf_reader.pages), max_pages)
                text = ""

                for page_num in range(num_pages):
                    try:
                        page = pdf_reader.pages[page_num]
                        page_text = page.extract_text()
                        text += page_text + "\n\n"
                    except Exception as e:
                        print(f"Error extracting text from page {page_num}: {str(e)}")
                        continue

                extracted = text.strip()
                print(f"DEBUG - Extracted {len(extracted)} characters from {num_pages} pages")
                if len(extracted) > 0:
                    print(f"DEBUG - First 100 chars: {extracted[:100]}...")
                return extracted
        except Exception as e:
            print(f"Error processing PDF {pdf_path}: {str(e)}")
            return ""

    def get_default_metadata(self) -> Dict:
        """Return default metadata structure with unknown values."""
        return {
            "title": "unknown",
            "authors": ["unknown"],
            "year": "unknown",
            "journal": "unknown",
            "doi": "unknown",
            "keywords": [],
            "abstract": "unknown"
        }

    def extract_metadata_from_pdf(self, pdf_path: str) -> Dict[str, str]:
        """Extract metadata from PDF by extracting first 3 pages locally and sending text to Gemini."""
        max_retries = 3
        retry_delay = 2

        # Extract text from first 3 pages using PyPDF2
        extracted_text = self.extract_text_from_pdf(pdf_path, max_pages=3)

        if not extracted_text:
            print("Warning: No text extracted from PDF")
            return self.get_default_metadata()

        for attempt in range(max_retries):
            try:
                print(f"Sending extracted text to Gemini API...")

                # Create prompt for metadata extraction
                prompt = f"""{self.system_prompt}

Extract bibliographic information from this text:

{extracted_text}"""

                # Generate content using the new SDK structure
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )

                content = response.text.strip()
                print(f"DEBUG - Gemini response length: {len(content)} chars")

                # Clean markdown code blocks if present
                if content.startswith("```json"):
                    content = content.replace("```json", "").replace("```", "").strip()
                elif content.startswith("```"):
                    content = content.replace("```", "").strip()

                # Try to parse as JSON
                try:
                    metadata = json.loads(content)
                    print(f"DEBUG - Successfully parsed JSON response")
                except json.JSONDecodeError as je:
                    print(f"Warning: JSON parsing failed: {je}")
                    print(f"DEBUG - Raw response: {content[:200]}...")
                    metadata = self.get_default_metadata()

                # Ensure all required fields exist
                default_metadata = self.get_default_metadata()
                for key in default_metadata:
                    if key not in metadata:
                        metadata[key] = default_metadata[key]

                return metadata

            except Exception as e:
                print(f"Error details: {type(e).__name__}: {str(e)}")

                if attempt < max_retries - 1:
                    print(f"Attempt {attempt + 1} failed. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    print(f"Error extracting metadata after {max_retries} attempts: {str(e)}")
                    return self.get_default_metadata()

    def normalize_metadata(self, metadata: Dict) -> Dict:
        """Normalize metadata to ensure consistent format."""
        normalized = metadata.copy()
        
        # Normalize authors to list of strings
        if 'authors' in normalized:
            if isinstance(normalized['authors'], list):
                author_strings = []
                for author in normalized['authors']:
                    if isinstance(author, dict):
                        # Extract name from dictionary
                        name = author.get('name', '')
                        if not name:
                            name = f"{author.get('first_name', '')} {author.get('last_name', '')}".strip()
                        if not name:
                            name = author.get('full_name', '')
                        if name:
                            author_strings.append(name)
                    else:
                        author_strings.append(str(author))
                normalized['authors'] = author_strings if author_strings else ["unknown"]
            elif isinstance(normalized['authors'], str):
                # Split string into list if it contains common separators
                if ',' in normalized['authors'] or ';' in normalized['authors']:
                    authors = [a.strip() for a in normalized['authors'].replace(';', ',').split(',')]
                    normalized['authors'] = [a for a in authors if a]
                else:
                    normalized['authors'] = [normalized['authors']] if normalized['authors'] else ["unknown"]
            else:
                normalized['authors'] = ["unknown"]
        
        # Normalize keywords to list of strings
        if 'keywords' in normalized:
            if isinstance(normalized['keywords'], list):
                normalized['keywords'] = [str(k) for k in normalized['keywords']]
            elif isinstance(normalized['keywords'], str):
                if ',' in normalized['keywords'] or ';' in normalized['keywords']:
                    keywords = [k.strip() for k in normalized['keywords'].replace(';', ',').split(',')]
                    normalized['keywords'] = [k for k in keywords if k]
                else:
                    normalized['keywords'] = [normalized['keywords']] if normalized['keywords'] else []
            else:
                normalized['keywords'] = []
        
        return normalized

    def process_directory(self, directory_path: str) -> None:
        """Process all PDF files in a directory and subdirectories, skipping already processed files."""
        # Load existing data
        processed_files = self.load_processed_files()
        results = self.load_existing_metadata()
        
        # Get all PDF files recursively
        pdf_files = list(Path(directory_path).rglob('*.pdf'))
        
        # Filter out already processed files
        unprocessed_files = []
        for pdf_path in pdf_files:
            # Use relative path from the base directory for consistency
            relative_path = str(pdf_path.relative_to(directory_path))
            if relative_path not in processed_files:
                unprocessed_files.append((pdf_path, relative_path))
        
        if not unprocessed_files:
            print("All PDF files have already been processed.")
            return
        
        print(f"\nFound {len(pdf_files)} total PDF files.")
        print(f"Already processed: {len(processed_files)}")
        print(f"To process: {len(unprocessed_files)}")
        
        # Process unprocessed files
        for i, (pdf_path, relative_path) in enumerate(unprocessed_files, 1):
            print(f"\n[{i}/{len(unprocessed_files)}] Processing {relative_path}...")
            
            try:
                # Use new SDK approach - upload PDF directly to Gemini
                metadata = self.extract_metadata_from_pdf(str(pdf_path))
                metadata['filename'] = pdf_path.name
                metadata['relative_path'] = relative_path
                metadata['full_path'] = str(pdf_path)
                
                # Normalize metadata format
                metadata = self.normalize_metadata(metadata)
            
                # Print extracted information
                print("\nExtracted Information:")
                print("-" * 50)
                print(f"Filename: {metadata['filename']}")
                print(f"Path: {metadata['relative_path']}")
                print(f"Title: {metadata['title']}")
                print(f"Authors: {', '.join(metadata['authors'])}")
                print(f"Year: {metadata['year']}")
                print(f"Journal/Conference: {metadata['journal']}")
                print(f"DOI: {metadata['doi']}")
                print(f"Keywords: {', '.join(metadata['keywords'])}")
                print("\nAbstract:")
                print("-" * 50)
                print(metadata['abstract'][:200] + "..." if len(metadata['abstract']) > 200 else metadata['abstract'])
                print("-" * 50)
            
                # Add to results and save
                results.append(metadata)
                
                # Save intermediate results
                with open(self.metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                
                # Mark file as processed only if everything succeeded
                self.save_processed_file(relative_path)
                
                print(f"✓ Saved metadata and marked as processed")
                
            except Exception as e:
                print(f"\n❌ Error processing {relative_path}: {str(e)}")
                print("Skipping this file and continuing...")
                continue

    def reset_processing_status(self) -> None:
        """Reset the processing status (useful for reprocessing all files)."""
        if os.path.exists(self.processed_files_path):
            os.remove(self.processed_files_path)
            print(f"Removed {self.processed_files_path}")
        if os.path.exists(self.metadata_path):
            backup_name = f"metadata_backup_{int(time.time())}.json"
            os.rename(self.metadata_path, backup_name)
            print(f"Backed up {self.metadata_path} to {backup_name}")

def main():
    # Get directory path from user
    directory = input("Enter the directory path containing PDF papers: ").strip()
    
    if not os.path.exists(directory):
        print(f"Error: Directory '{directory}' does not exist.")
        return
    
    # Check for API key
    if not GEMINI_API_KEY:
        print("\nError: GEMINI_API_KEY not found.")
        print("\nYou can set it in one of these ways:")
        print("1. Create a .env file in the script directory with: GEMINI_API_KEY=your-api-key-here")
        print("2. Set it as an environment variable:")
        print("   - Windows: set GEMINI_API_KEY=your-api-key-here")
        print("   - Linux/Mac: export GEMINI_API_KEY='your-api-key-here'")
        print("\nMake sure you have python-dotenv installed: pip install python-dotenv")
        print("\nGet your Gemini API key from: https://makersuite.google.com/app/apikey")
        return
    
    # Check for reset option
    if os.path.exists('processed_files.json'):
        reset = input("\nFound existing processing data. Reset and start fresh? (y/N): ").strip().lower()
        if reset == 'y':
            processor = PaperProcessor(GEMINI_API_KEY)
            processor.reset_processing_status()

    # Initialize processor with Gemini API key
    processor = PaperProcessor(GEMINI_API_KEY)
    
    # Process all papers
    try:
        processor.process_directory(directory)
        print("\n✅ Processing complete. Results saved to metadata.json")
        
        # Show summary
        processed_files = processor.load_processed_files()
        metadata = processor.load_existing_metadata()
        print(f"\nSummary:")
        print(f"- Total files processed: {len(processed_files)}")
        print(f"- Total metadata entries: {len(metadata)}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Processing interrupted. Progress has been saved.")
        print("Run the script again to resume from where you left off.")

if __name__ == "__main__":
    main()