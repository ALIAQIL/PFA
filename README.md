# Smart Product Recommender for Gaming Gear using RAG and Amazon Scraping

## Overview

This project implements a smart recommendation system specifically designed for gaming gear. It leverages the power of Retrieval-Augmented Generation (RAG) combined with real-time product data scraped from Amazon to provide users with relevant and up-to-date gaming peripheral recommendations. The system aims to understand user needs expressed in natural language and suggest products (like mice, keyboards, headsets, etc.) based on features, reviews, and specifications extracted directly from Amazon product pages.

The core idea is to overcome the limitations of static recommendation datasets by continuously fetching fresh information from Amazon. The RAG model then uses this retrieved information to generate informed and contextually appropriate recommendations, going beyond simple keyword matching.

## Features

*   **Amazon Data Scraping:** Employs web scraping techniques (using Selenium and potentially proxy management) to gather product details, specifications, prices, and potentially reviews from Amazon for a range of gaming gear.
*   **Data Processing:** Cleans and structures the scraped data, preparing it for indexing and retrieval.
*   **Vector Store Integration:** Uses LanceDB to create and manage a vector store of the processed product information, enabling efficient similarity searches.
*   **RAG-Based Recommendations:** Integrates a RAG model (specific model details would be added here) that takes a user query (e.g., "best lightweight wireless mouse for FPS games"), retrieves relevant product information from the LanceDB vector store, and generates a natural language recommendation based on the retrieved context.
*   **Proxy Management (Optional):** Includes utilities for managing and validating proxies to facilitate robust and large-scale scraping operations, mitigating potential IP blocks from Amazon.
*   **Tesseract OCR Integration (Optional):** Provides a framework for integrating Tesseract OCR to extract text from images, potentially used for analyzing product images or screenshots (requires manual setup, see section below).

## How it Works

1.  **Crawling & Scraping:** The `amazon_crawler.py` script likely identifies relevant gaming gear product links on Amazon. Then, `amazon_scraper.py` visits these links, potentially using `chromedriver.exe` and managed proxies (`proxy_manager.py`, `validate_proxies.py`), to extract detailed product information.
2.  **Data Storage & Processing:** The raw scraped data (initially stored in `amazon_data.json`) is processed and potentially converted to other formats like CSV (`json_to_csv.py`, `amazon_scraping_data.csv`) by `data_processing.py`.
3.  **Vector Embedding & Indexing:** The processed product data is then converted into vector embeddings and stored in a LanceDB vector database (`lancedb_data/amazon_multi_vector_store.lance`). This allows for semantic searching based on user queries.
4.  **Recommendation Generation:** The `rag_recommendation.py` script takes a user's natural language query. It converts the query into an embedding, searches the LanceDB database for the most similar product embeddings (and their associated text data), and feeds this retrieved information along with the original query to a large language model (LLM). The LLM, acting as the generator in the RAG pipeline, synthesizes the information to produce a coherent and relevant product recommendation.
5.  **(Optional) OCR Processing:** If implemented and configured, the `tesseract/OCR.py` script can be called to extract text from image files related to the products.

## Installation

Before running the project, ensure you have Python installed (preferably version 3.8 or higher). You will also need Git to clone the repository.

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/ALIAQIL/Smart_Product_Recommender_for_Gaming-Gear_using_RAG_and_Amazon_Scraping.git
    cd Smart_Product_Recommender_for_Gaming-Gear_using_RAG_and_Amazon_Scraping
    ```

2.  **Set up a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install Dependencies:** Use the provided `requirements.txt` file (or create one based on the suggestions) listing all necessary libraries (e.g., `selenium`, `pandas`, `lancedb`, `requests`, potentially a library for the LLM like `transformers` or `openai`). Then install them:
    ```bash
    pip install -r requirements.txt
    ```
    *Note: If you plan to use the OCR functionality, ensure `pytesseract` and `Pillow` are included in your `requirements.txt`.*

4.  **Install ChromeDriver:** This project uses Selenium, which requires a WebDriver compatible with your installed Chrome browser. Download the appropriate ChromeDriver executable from the [official ChromeDriver website](https://chromedriver.chromium.org/downloads) and place it either in your system's PATH or directly in the project directory. *Alternatively, consider using the `webdriver-manager` Python package (recommended) to handle this automatically.*

5.  **(Optional) Install Tesseract OCR Engine:** If you intend to use the OCR features, follow the instructions in the "Optional: Tesseract OCR Integration" section below to install the Tesseract engine on your system.

## Usage

*(Detailed usage instructions would depend on the final structure and entry points of the scripts. Below is a hypothetical example.)*

1.  **Run the Scraper (if needed):** Execute the scraping scripts to gather fresh data from Amazon. You might need to configure proxies or adjust scraping parameters.
    ```bash
    python amazon_crawler.py
    python amazon_scraper.py
    ```

2.  **Process Data and Build Vector Store:** Run the data processing and indexing scripts.
    ```bash
    python data_processing.py
    # (Script to build/update LanceDB store)
    ```

3.  **Get Recommendations:** Use the RAG recommendation script, providing your query.
    ```bash
    python rag_recommendation.py --query "Suggest a quiet mechanical keyboard for typing and gaming"
    ```
    *(The exact command-line arguments or method of interaction might differ.)*

4.  **(Optional) Use OCR:** If you have set up Tesseract and added `OCR.py`, you can use it as needed (see example usage in the OCR section below).

## Optional: Tesseract OCR Integration (OCR.py)

This section describes how to set up and use the Optical Character Recognition (OCR) functionality, intended to be handled by an `OCR.py` script located in the `tesseract/` directory.

**Note:** The `OCR.py` script itself is not included in the base repository. You need to add your implementation of `OCR.py` to the `tesseract/` directory.

### Prerequisites: Installing Tesseract OCR Engine

Before using `OCR.py`, you must install the Tesseract OCR engine on your system. The installation process varies depending on your operating system:

*   **Ubuntu/Debian:**
    ```bash
    sudo apt update
    sudo apt install tesseract-ocr
    # Install language data (e.g., for English)
    sudo apt install tesseract-ocr-eng
    # For other languages, replace 'eng' with the appropriate code (e.g., 'fra' for French)
    # Find language codes here: https://tesseract-ocr.github.io/tessdoc/Data-Files-in-v4.00%2B.html
    ```

*   **macOS:**
    ```bash
    brew install tesseract
    # Language data is usually included or can be installed via brew as well
    brew install tesseract-lang
    ```

*   **Windows:**
    Download the installer from the [Tesseract at UB Mannheim page](https://github.com/UB-Mannheim/tesseract/wiki). During installation, make sure to:
    1.  Select the language data packs you need.
    2.  **Important:** Add the Tesseract installation directory to your system's PATH environment variable. This allows Python (and the command line) to find the `tesseract.exe` executable.

*   **Verify Installation:**
    Open your terminal or command prompt and run:
    ```bash
    tesseract --version
    ```
    This should display the installed Tesseract version.

### Python Wrapper: pytesseract

This project typically uses the `pytesseract` library to interact with the Tesseract engine from Python. Ensure it's included in your main `requirements.txt` file (as mentioned in the Installation section) or install it manually:

```bash
pip install pytesseract Pillow
```
(`Pillow` is required for image handling).

### Setup: Adding OCR.py

1.  Obtain or create your `OCR.py` script.
2.  Place the `OCR.py` file inside the `tesseract/` directory within the project structure.

### Usage (Example)

Your `OCR.py` script should ideally provide a function or command-line interface to perform OCR on an image file. Here’s a conceptual example of how you might use it (the actual implementation in `OCR.py` might differ):

**Example Python Usage (within another script):**

```python
# Assuming OCR.py is in the tesseract directory
# and provides a function like extract_text_from_image

# Adjust import path based on your project structure
from tesseract.OCR import extract_text_from_image

image_path = '/path/to/your/image.png'

try:
    extracted_text = extract_text_from_image(image_path)
    print("--- Extracted Text ---")
    print(extracted_text)
    print("----------------------")
except FileNotFoundError:
    print(f"Error: Image file not found at {image_path}")
except Exception as e:
    print(f"An error occurred during OCR: {e}")

```

**Example Command-Line Usage (if OCR.py supports it):**

```bash
python tesseract/OCR.py --image /path/to/your/image.png
```

Refer to the specific implementation within your `OCR.py` for exact usage instructions.

### OCR Dependencies

*   Tesseract OCR Engine (System installation required)
*   Python 3.x
*   `pytesseract` Python library
*   `Pillow` Python library

Make sure these dependencies are met for the OCR functionality to work correctly.

## Project Structure (Current)

*(This section describes the current file layout. It's recommended to refactor based on the cleanup suggestions provided earlier.)*

```
├── lancedb_data/
│   └── amazon_multi_vector_store.lance  # LanceDB vector store
├── tesseract/                          # Directory for Tesseract OCR related scripts (e.g., OCR.py)
├── amazon_crawler.py                 # Script to find product links
├── amazon_data.json                  # Raw scraped data (JSON) - Should be gitignored
├── amazon_scraper.py                 # Script to scrape product details
├── amazon_scraping_data.csv          # Processed scraped data (CSV) - Should be gitignored
├── chromedriver.exe                  # WebDriver for Selenium (Should be gitignored)
├── tesseract/
│   └── OCR.py  # CAPTCHA solver
├── data_processing.py                # Script for cleaning/processing data
├── json_to_csv.py                    # Utility to convert JSON to CSV
├── product_links.json                # List of product URLs to scrape - Should be gitignored
├── proxy_manager.py                  # Script for handling proxies
├── rag_recommendation.py             # Main script for generating recommendations
└── validate_proxies.py               # Utility to check proxy validity
```


