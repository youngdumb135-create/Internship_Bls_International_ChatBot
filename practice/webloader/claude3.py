import os
import json
import time
import logging
import hashlib
import requests
from collections import deque
from urllib.parse import urlparse, urlunparse, urljoin
from datetime import datetime
from typing import Dict, List, Any, Optional

# Web scraping imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, WebDriverException
import validators

# HTML parsing
from bs4 import BeautifulSoup
import pandas as pd

# PDF processing imports
import fitz  # PyMuPDF
import pdfplumber
import re
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ScrapedContent:
    """Structure for all scraped content"""
    url: str
    country: str
    content_type: str  # 'text', 'table', 'pdf', 'list', 'heading'
    content: str
    metadata: Dict[str, Any]
    page_title: str
    section: Optional[str] = None
    subsection: Optional[str] = None
    timestamp: str = None

class PDFProcessor:
    """Handles PDF extraction with all content types"""
    
    def extract_pdf_content(self, pdf_path: str, source_url: str, country: str) -> List[ScrapedContent]:
        """Extract all content from PDF"""
        content_list = []
        
        try:
            # Extract with pdfplumber for tables
            table_content = self._extract_tables_from_pdf(pdf_path)
            
            # Extract with PyMuPDF for text structure
            text_content = self._extract_text_structure_from_pdf(pdf_path)
            
            # Combine and format
            for item in table_content + text_content:
                content_list.append(ScrapedContent(
                    url=source_url,
                    country=country,
                    content_type=item['type'],
                    content=item['content'],
                    metadata={
                        'source': 'pdf',
                        'pdf_path': pdf_path,
                        'page_number': item.get('page', 0),
                        **item.get('metadata', {})
                    },
                    page_title=item.get('title', 'PDF Document'),
                    timestamp=datetime.now().isoformat()
                ))
                
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {e}")
        
        return content_list
    
    def _extract_tables_from_pdf(self, pdf_path: str) -> List[Dict]:
        """Extract tables using pdfplumber"""
        tables = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_tables = page.extract_tables()
                    
                    for table_idx, table in enumerate(page_tables):
                        if table and len(table) > 1:
                            formatted_table = self._format_table(table)
                            if formatted_table:
                                tables.append({
                                    'type': 'table',
                                    'content': formatted_table,
                                    'page': page_num,
                                    'metadata': {
                                        'table_index': table_idx,
                                        'rows': len(table),
                                        'columns': len(table[0]) if table else 0
                                    }
                                })
        except Exception as e:
            logger.error(f"Error extracting tables from PDF: {e}")
        
        return tables
    
    def _extract_text_structure_from_pdf(self, pdf_path: str) -> List[Dict]:
        """Extract structured text using PyMuPDF"""
        text_content = []
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                blocks = page.get_text("dict")
                
                for block in blocks.get("blocks", []):
                    if "lines" in block:
                        block_text = self._extract_block_text(block)
                        
                        if block_text.strip():
                            content_type, processed_content = self._analyze_text_content(block_text)
                            
                            text_content.append({
                                'type': content_type,
                                'content': processed_content,
                                'page': page_num,
                                'metadata': self._get_text_formatting_info(block)
                            })
            
            doc.close()
            
        except Exception as e:
            logger.error(f"Error extracting text structure from PDF: {e}")
        
        return text_content
    
    def _format_table(self, table: List[List]) -> str:
        """Format table for knowledge base"""
        if not table or len(table) < 1:
            return ""
        
        headers = [str(cell).strip() if cell else f"Col_{i}" for i, cell in enumerate(table[0])]
        rows = table[1:]
        
        # Create structured format
        formatted = f"Table with columns: {', '.join(headers)}\n\n"
        
        for row_idx, row in enumerate(rows):
            row_data = []
            for col_idx, cell in enumerate(row):
                if col_idx < len(headers) and cell:
                    cell_value = str(cell).strip()
                    if cell_value:
                        row_data.append(f"{headers[col_idx]}: {cell_value}")
            
            if row_data:
                formatted += f"Row {row_idx + 1}: {' | '.join(row_data)}\n"
        
        return formatted
    
    def _extract_block_text(self, block: Dict) -> str:
        """Extract text from a block"""
        text = ""
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text += span.get("text", "")
        return text
    
    def _analyze_text_content(self, text: str) -> tuple:
        """Analyze text to determine type"""
        lines = text.split('\n')
        
        # Check for lists
        list_patterns = [r'^\s*[•\-\*\+]\s+', r'^\s*\d+[\.\)]\s+', r'^\s*[a-zA-Z][\.\)]\s+']
        list_lines = sum(1 for line in lines if any(re.match(pattern, line) for pattern in list_patterns))
        
        if list_lines >= 2:
            return "list", self._format_list(text)
        
        # Check for headings (short, title case, no ending period)
        if len(text) < 100 and '\n' not in text.strip() and (text.isupper() or text.istitle()) and not text.strip().endswith('.'):
            return "heading", text.strip()
        
        return "text", text.strip()
    
    def _format_list(self, text: str) -> str:
        """Format list content"""
        lines = text.split('\n')
        formatted_items = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove list markers and format
            cleaned_line = re.sub(r'^\s*[•\-\*\+]\s*', '• ', line)
            cleaned_line = re.sub(r'^\s*\d+[\.\)]\s*', '• ', cleaned_line)
            cleaned_line = re.sub(r'^\s*[a-zA-Z][\.\)]\s*', '• ', cleaned_line)
            
            if cleaned_line and not cleaned_line.startswith('•'):
                cleaned_line = '• ' + cleaned_line
            
            if cleaned_line:
                formatted_items.append(cleaned_line)
        
        return '\n'.join(formatted_items)
    
    def _get_text_formatting_info(self, block: Dict) -> Dict:
        """Extract formatting metadata"""
        metadata = {}
        
        fonts = set()
        sizes = set()
        
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                if "font" in span:
                    fonts.add(span["font"])
                if "size" in span:
                    sizes.add(span["size"])
        
        if fonts:
            metadata["fonts"] = list(fonts)
        if sizes:
            metadata["font_sizes"] = list(sizes)
        
        return metadata

class CountryDetector:
    """Detects and extracts country information from URLs and content"""
    
    def __init__(self):
        # Common country indicators in URLs and content
        self.country_patterns = {
            'slovakia': ['slovakia', 'slovak', 'bratislava'],
            'india': ['india', 'indian', 'delhi', 'mumbai', 'bangalore'],
            'usa': ['usa', 'america', 'united-states', 'us'],
            'uk': ['uk', 'united-kingdom', 'britain', 'london'],
            'canada': ['canada', 'canadian', 'toronto', 'vancouver'],
            'australia': ['australia', 'australian', 'sydney', 'melbourne'],
            'germany': ['germany', 'german', 'berlin', 'munich'],
            'france': ['france', 'french', 'paris'],
            # Add more countries as needed
        }
    
    def detect_country_from_url(self, url: str) -> str:
        """Detect country from URL path or domain"""
        url_lower = url.lower()
        
        for country, patterns in self.country_patterns.items():
            if any(pattern in url_lower for pattern in patterns):
                return country
        
        return 'general'  # Default if no specific country detected
    
    def detect_country_from_content(self, content: str, page_title: str = "") -> str:
        """Detect country from page content"""
        combined_text = (content + " " + page_title).lower()
        
        country_scores = {}
        for country, patterns in self.country_patterns.items():
            score = sum(combined_text.count(pattern) for pattern in patterns)
            if score > 0:
                country_scores[country] = score
        
        if country_scores:
            return max(country_scores, key=country_scores.get)
        
        return 'general'

class ComprehensiveWebScraper:
    """Main scraper class that handles everything"""
    
    def __init__(self, base_url: str, output_dir: str = "scraped_data"):
        self.base_url = base_url
        self.base_domain = urlparse(base_url).netloc
        self.output_dir = output_dir
        
        # Initialize components
        self.country_detector = CountryDetector()
        self.pdf_processor = PDFProcessor()
        
        # URL tracking
        self.to_visit = deque([base_url])
        self.visited_urls = set()
        self.queued_urls = set([base_url])
        
        # Results storage
        self.all_scraped_content = []
        self.country_data = {}  # Organized by country
        self.pdf_downloads = {}  # Track downloaded PDFs
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(f"{output_dir}/pdfs", exist_ok=True)
    
    def get_driver_options(self) -> Options:
        """Configure Chrome driver"""
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        return options
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL should be crawled"""
        if not url or not validators.url(url):
            return False
        
        parsed = urlparse(url)
        
        # Skip fragments and mailto links
        if url.startswith('mailto:') or url.startswith('tel:'):
            return False
        
        # Only crawl same domain
        return parsed.netloc.endswith(self.base_domain)
    
    def download_pdf(self, pdf_url: str, country: str) -> Optional[str]:
        """Download PDF file"""
        try:
            # Create unique filename
            url_hash = hashlib.md5(pdf_url.encode()).hexdigest()[:8]
            filename = f"{country}_{url_hash}.pdf"
            filepath = os.path.join(self.output_dir, "pdfs", filename)
            
            # Skip if already downloaded
            if filepath in self.pdf_downloads.values():
                return filepath
            
            # Download PDF
            response = requests.get(pdf_url, timeout=30)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            self.pdf_downloads[pdf_url] = filepath
            logger.info(f"Downloaded PDF: {pdf_url} -> {filepath}")
            
            return filepath
            
        except Exception as e:
            logger.error(f"Error downloading PDF {pdf_url}: {e}")
            return None
    
    def extract_tables_from_html(self, soup: BeautifulSoup, url: str, country: str) -> List[ScrapedContent]:
        """Extract all tables from HTML"""
        tables = []
        
        try:
            html_tables = soup.find_all('table')
            
            for idx, table in enumerate(html_tables):
                # Convert HTML table to structured format
                table_data = []
                
                # Get headers
                headers = []
                header_row = table.find('tr')
                if header_row:
                    for th in header_row.find_all(['th', 'td']):
                        headers.append(th.get_text(strip=True))
                
                # Get all rows
                for row in table.find_all('tr')[1:]:  # Skip header row
                    row_data = []
                    for cell in row.find_all(['td', 'th']):
                        row_data.append(cell.get_text(strip=True))
                    if any(row_data):  # Only add non-empty rows
                        table_data.append(row_data)
                
                if headers and table_data:
                    formatted_table = self._format_html_table(headers, table_data)
                    
                    tables.append(ScrapedContent(
                        url=url,
                        country=country,
                        content_type='table',
                        content=formatted_table,
                        metadata={
                            'source': 'html',
                            'table_index': idx,
                            'rows': len(table_data),
                            'columns': len(headers)
                        },
                        page_title=soup.title.string if soup.title else "",
                        timestamp=datetime.now().isoformat()
                    ))
                    
        except Exception as e:
            logger.error(f"Error extracting tables from {url}: {e}")
        
        return tables
    
    def _format_html_table(self, headers: List[str], rows: List[List[str]]) -> str:
        """Format HTML table for knowledge base"""
        formatted = f"Table with columns: {', '.join(headers)}\n\n"
        
        for row_idx, row in enumerate(rows):
            row_data = []
            for col_idx, cell in enumerate(row):
                if col_idx < len(headers) and cell:
                    row_data.append(f"{headers[col_idx]}: {cell}")
            
            if row_data:
                formatted += f"Row {row_idx + 1}: {' | '.join(row_data)}\n"
        
        return formatted
    
    def extract_text_content(self, soup: BeautifulSoup, url: str, country: str) -> List[ScrapedContent]:
        """Extract structured text content"""
        content_list = []
        
        try:
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Extract different content types
            
            # 1. Headings
            for level in range(1, 7):  # h1 to h6
                headings = soup.find_all(f'h{level}')
                for heading in headings:
                    text = heading.get_text(strip=True)
                    if text:
                        content_list.append(ScrapedContent(
                            url=url,
                            country=country,
                            content_type='heading',
                            content=text,
                            metadata={'heading_level': level, 'source': 'html'},
                            page_title=soup.title.string if soup.title else "",
                            timestamp=datetime.now().isoformat()
                        ))
            
            # 2. Lists
            for list_tag in soup.find_all(['ul', 'ol']):
                items = []
                for li in list_tag.find_all('li'):
                    item_text = li.get_text(strip=True)
                    if item_text:
                        items.append(f"• {item_text}")
                
                if items:
                    content_list.append(ScrapedContent(
                        url=url,
                        country=country,
                        content_type='list',
                        content='\n'.join(items),
                        metadata={'list_type': list_tag.name, 'item_count': len(items), 'source': 'html'},
                        page_title=soup.title.string if soup.title else "",
                        timestamp=datetime.now().isoformat()
                    ))
            
            # 3. Paragraphs and main content
            main_content_tags = ['p', 'div', 'section', 'article', 'main']
            
            for tag_name in main_content_tags:
                elements = soup.find_all(tag_name)
                
                for element in elements:
                    # Skip if it contains tables or lists (already processed)
                    if element.find(['table', 'ul', 'ol']):
                        continue
                    
                    text = element.get_text(strip=True)
                    
                    # Only process substantial text content
                    if len(text) > 50:  # Minimum length threshold
                        content_list.append(ScrapedContent(
                            url=url,
                            country=country,
                            content_type='text',
                            content=text,
                            metadata={'source': 'html', 'tag': tag_name},
                            page_title=soup.title.string if soup.title else "",
                            timestamp=datetime.now().isoformat()
                        ))
                        
        except Exception as e:
            logger.error(f"Error extracting text content from {url}: {e}")
        
        return content_list
    
    def scrape_page(self, driver: webdriver.Chrome, url: str) -> List[ScrapedContent]:
        """Scrape all content from a single page"""
        all_content = []
        
        try:
            driver.get(url)
            
            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Get page source for BeautifulSoup
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Detect country
            page_title = soup.title.string if soup.title else ""
            body_text = soup.get_text()[:1000]  # First 1000 chars for country detection
            
            country_from_url = self.country_detector.detect_country_from_url(url)
            country_from_content = self.country_detector.detect_country_from_content(body_text, page_title)
            
            # Prioritize URL-based detection
            country = country_from_url if country_from_url != 'general' else country_from_content
            
            logger.info(f"Scraping {url} - Detected country: {country}")
            
            # Extract all content types
            
            # 1. HTML Tables
            table_content = self.extract_tables_from_html(soup, url, country)
            all_content.extend(table_content)
            
            # 2. Text content (headings, paragraphs, lists)
            text_content = self.extract_text_content(soup, url, country)
            all_content.extend(text_content)
            
            # 3. PDF links
            pdf_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.lower().endswith('.pdf'):
                    full_pdf_url = urljoin(url, href)
                    pdf_links.append(full_pdf_url)
            
            # Process PDFs
            for pdf_url in pdf_links:
                pdf_path = self.download_pdf(pdf_url, country)
                if pdf_path:
                    pdf_content = self.pdf_processor.extract_pdf_content(pdf_path, pdf_url, country)
                    all_content.extend(pdf_content)
            
            # Find new URLs to crawl
            new_urls = self.extract_urls(driver, url)
            
            return all_content, new_urls
            
        except Exception as e:
            logger.error(f"Error scraping page {url}: {e}")
            return [], []
    
    def extract_urls(self, driver: webdriver.Chrome, current_url: str) -> List[str]:
        """Extract all URLs from current page"""
        new_urls = []
        
        try:
            links = driver.find_elements(By.TAG_NAME, "a")
            
            for link in links:
                href = link.get_attribute("href")
                if href:
                    absolute_url = urljoin(self.base_url, href)
                    
                    if (self.is_valid_url(absolute_url) and 
                        absolute_url not in self.visited_urls and 
                        absolute_url not in self.queued_urls):
                        
                        new_urls.append(absolute_url)
                        self.queued_urls.add(absolute_url)
                        
        except Exception as e:
            logger.error(f"Error extracting URLs from {current_url}: {e}")
        
        return new_urls
    
    def organize_data_by_country(self):
        """Organize all scraped data by country"""
        self.country_data = {}
        
        for content in self.all_scraped_content:
            country = content.country
            
            if country not in self.country_data:
                self.country_data[country] = {
                    'text': [],
                    'tables': [],
                    'lists': [],
                    'headings': [],
                    'pdfs': []
                }
            
            content_type = content.content_type
            if content_type in ['text']:
                self.country_data[country]['text'].append(content)
            elif content_type in ['table', 'table_structured', 'table_natural']:
                self.country_data[country]['tables'].append(content)
            elif content_type == 'list':
                self.country_data[country]['lists'].append(content)
            elif content_type == 'heading':
                self.country_data[country]['headings'].append(content)
            elif content.metadata.get('source') == 'pdf':
                self.country_data[country]['pdfs'].append(content)
    
    def save_data(self):
        """Save all scraped data in organized format"""
        
        # Save complete dataset
        all_data = []
        for content in self.all_scraped_content:
            all_data.append({
                'url': content.url,
                'country': content.country,
                'content_type': content.content_type,
                'content': content.content,
                'metadata': content.metadata,
                'page_title': content.page_title,
                'section': content.section,
                'subsection': content.subsection,
                'timestamp': content.timestamp
            })
        
        # Save complete data
        with open(f"{self.output_dir}/complete_scraped_data.json", 'w', encoding='utf-8') as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False)
        
        # Save country-organized data
        country_organized = {}
        for country, data in self.country_data.items():
            country_organized[country] = {}
            
            for content_type, content_list in data.items():
                country_organized[country][content_type] = []
                
                for content in content_list:
                    country_organized[country][content_type].append({
                        'url': content.url,
                        'content': content.content,
                        'metadata': content.metadata,
                        'page_title': content.page_title,
                        'timestamp': content.timestamp
                    })
        
        with open(f"{self.output_dir}/country_organized_data.json", 'w', encoding='utf-8') as f:
            json.dump(country_organized, f, indent=2, ensure_ascii=False)
        
        # Save statistics
        stats = {
            'total_content_items': len(self.all_scraped_content),
            'countries_found': list(self.country_data.keys()),
            'content_by_country': {
                country: {
                    'total': sum(len(content_list) for content_list in data.values()),
                    'by_type': {content_type: len(content_list) for content_type, content_list in data.items()}
                }
                for country, data in self.country_data.items()
            },
            'urls_visited': len(self.visited_urls),
            'pdfs_downloaded': len(self.pdf_downloads)
        }
        
        with open(f"{self.output_dir}/scraping_statistics.json", 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Data saved to {self.output_dir}")
        logger.info(f"Statistics: {stats}")
    
    def crawl_and_scrape(self):
        """Main function to crawl and scrape everything"""
        options = self.get_driver_options()
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        try:
            while self.to_visit:
                current_url = self.to_visit.popleft()
                
                if current_url in self.visited_urls:
                    continue
                
                logger.info(f"Processing: {current_url}")
                
                try:
                    # Scrape the page
                    page_content, new_urls = self.scrape_page(driver, current_url)
                    
                    # Add content to results
                    self.all_scraped_content.extend(page_content)
                    
                    # Add new URLs to queue
                    for new_url in new_urls:
                        self.to_visit.append(new_url)
                    
                    # Mark as visited
                    self.visited_urls.add(current_url)
                    
                    # Small delay to be respectful
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error processing {current_url}: {e}")
                    continue
                    
        finally:
            driver.quit()
        
        # Organize and save data
        self.organize_data_by_country()
        self.save_data()
        
        return self.country_data

# Usage
if __name__ == "__main__":
    base_url = "https://www.blsslovakiavisa.com/"
    
    scraper = ComprehensiveWebScraper(base_url, "bls_slovakia_data")
    
    print("Starting comprehensive web scraping...")
    print("This will extract ALL content: text, tables, lists, PDFs, etc.")
    print("Data will be organized by country for your chatbot.")
    
    results = scraper.crawl_and_scrape()
    
    print(f"\nScraping completed!")
    print(f"Countries found: {list(results.keys())}")
    
    for country, data in results.items():
        total_items = sum(len(content_list) for content_list in data.values())
        print(f"{country}: {total_items} content items")
        print(f"  - Text: {len(data['text'])}")
        print(f"  - Tables: {len(data['tables'])}")
        print(f"  - Lists: {len(data['lists'])}")
        print(f"  - Headings: {len(data['headings'])}")
        print(f"  - PDF content: {len(data['pdfs'])}")

