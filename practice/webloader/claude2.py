import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import json
import time
import csv
from urllib.parse import urljoin, urlparse
import re
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BLSSlovakiaVisaScraper:
    def __init__(self, headless=True):
        self.base_url = "https://www.blsslovakiavisa.com/"
        self.visited_urls = set()
        self.scraped_data = []
        self.session = requests.Session()
        
        # Setup Selenium WebDriver
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
        
    def __del__(self):
        if hasattr(self, 'driver'):
            self.driver.quit()
    
    def extract_page_content(self, url):
        """Extract comprehensive content from a single page"""
        try:
            logger.info(f"Scraping: {url}")
            self.driver.get(url)
            
            # Wait for page to load
            time.sleep(3)
            
            # Try to handle any popups or modals
            try:
                close_buttons = self.driver.find_elements(By.CSS_SELECTOR, "[class*='close'], [class*='dismiss'], .modal-close")
                for button in close_buttons:
                    if button.is_displayed():
                        button.click()
                        time.sleep(1)
            except:
                pass
            
            # Get page source and parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Extract various types of content
            page_data = {
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'title': self.extract_title(soup),
                'meta_description': self.extract_meta_description(soup),
                'headings': self.extract_headings(soup),
                'paragraphs': self.extract_paragraphs(soup),
                'lists': self.extract_lists(soup),
                'tables': self.extract_tables(soup),
                'forms': self.extract_forms(soup),
                'links': self.extract_links(soup, url),
                'images': self.extract_images(soup, url),
                'contact_info': self.extract_contact_info(soup),
                'visa_info': self.extract_visa_specific_info(soup),
                'requirements': self.extract_requirements(soup),
                'procedures': self.extract_procedures(soup),
                'fees': self.extract_fees(soup),
                'office_locations': self.extract_office_locations(soup),
                'working_hours': self.extract_working_hours(soup),
                'documents': self.extract_document_info(soup),
                'faq': self.extract_faq(soup)
            }
            
            return page_data
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return None
    
    def extract_title(self, soup):
        """Extract page title"""
        title_tag = soup.find('title')
        return title_tag.get_text().strip() if title_tag else ""
    
    def extract_meta_description(self, soup):
        """Extract meta description"""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        return meta_desc.get('content', '').strip() if meta_desc else ""
    
    def extract_headings(self, soup):
        """Extract all headings (h1-h6)"""
        headings = []
        for i in range(1, 7):
            for heading in soup.find_all(f'h{i}'):
                text = heading.get_text().strip()
                if text:
                    headings.append({
                        'level': i,
                        'text': text,
                        'id': heading.get('id', ''),
                        'class': heading.get('class', [])
                    })
        return headings
    
    def extract_paragraphs(self, soup):
        """Extract all paragraph text"""
        paragraphs = []
        for p in soup.find_all('p'):
            text = p.get_text().strip()
            if text and len(text) > 10:  # Filter out very short paragraphs
                paragraphs.append(text)
        return paragraphs
    
    def extract_lists(self, soup):
        """Extract all lists (ul, ol)"""
        lists = []
        for list_tag in soup.find_all(['ul', 'ol']):
            items = []
            for li in list_tag.find_all('li'):
                text = li.get_text().strip()
                if text:
                    items.append(text)
            if items:
                lists.append({
                    'type': list_tag.name,
                    'items': items,
                    'class': list_tag.get('class', [])
                })
        return lists
    
    def extract_tables(self, soup):
        """Extract table data"""
        tables = []
        for table in soup.find_all('table'):
            rows = []
            for tr in table.find_all('tr'):
                cells = []
                for cell in tr.find_all(['td', 'th']):
                    cells.append(cell.get_text().strip())
                if cells:
                    rows.append(cells)
            if rows:
                tables.append({
                    'rows': rows,
                    'class': table.get('class', []),
                    'id': table.get('id', '')
                })
        return tables
    
    def extract_forms(self, soup):
        """Extract form information"""
        forms = []
        for form in soup.find_all('form'):
            fields = []
            for input_field in form.find_all(['input', 'select', 'textarea']):
                field_info = {
                    'type': input_field.get('type', input_field.name),
                    'name': input_field.get('name', ''),
                    'id': input_field.get('id', ''),
                    'placeholder': input_field.get('placeholder', ''),
                    'required': input_field.get('required') is not None
                }
                fields.append(field_info)
            
            if fields:
                forms.append({
                    'action': form.get('action', ''),
                    'method': form.get('method', 'get'),
                    'fields': fields
                })
        return forms
    
    def extract_links(self, soup, base_url):
        """Extract all internal links"""
        links = []
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            full_url = urljoin(base_url, href)
            
            # Only include links from the same domain
            if self.base_url in full_url:
                links.append({
                    'url': full_url,
                    'text': link.get_text().strip(),
                    'title': link.get('title', ''),
                    'class': link.get('class', [])
                })
        return links
    
    def extract_images(self, soup, base_url):
        """Extract image information"""
        images = []
        for img in soup.find_all('img'):
            src = img.get('src')
            if src:
                full_url = urljoin(base_url, src)
                images.append({
                    'src': full_url,
                    'alt': img.get('alt', ''),
                    'title': img.get('title', ''),
                    'class': img.get('class', [])
                })
        return images
    
    def extract_contact_info(self, soup):
        """Extract contact information"""
        contact_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'[\+]?[1-9]?[0-9]{7,15}',
            'address': r'\b\d+\s+\w+.*?(?=\b(?:Phone|Email|Tel|Fax|Website)\b|$)'
        }
        
        text = soup.get_text()
        contact_info = {}
        
        for info_type, pattern in contact_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                contact_info[info_type] = list(set(matches))
        
        return contact_info
    
    def extract_visa_specific_info(self, soup):
        """Extract visa-specific information"""
        visa_keywords = [
            'visa', 'schengen', 'tourism', 'business', 'transit',
            'appointment', 'application', 'processing time', 'validity'
        ]
        
        visa_content = []
        text = soup.get_text().lower()
        
        for keyword in visa_keywords:
            if keyword in text:
                # Find sentences containing the keyword
                sentences = re.split(r'[.!?]', soup.get_text())
                for sentence in sentences:
                    if keyword in sentence.lower() and len(sentence.strip()) > 20:
                        visa_content.append(sentence.strip())
        
        return visa_content
    
    def extract_requirements(self, soup):
        """Extract visa requirements"""
        requirements = []
        
        # Look for sections that might contain requirements
        requirement_indicators = [
            'requirement', 'document', 'needed', 'must', 'mandatory',
            'necessary', 'submit', 'provide', 'bring'
        ]
        
        for section in soup.find_all(['div', 'section', 'ul', 'ol']):
            section_text = section.get_text().lower()
            if any(indicator in section_text for indicator in requirement_indicators):
                if section.name in ['ul', 'ol']:
                    for li in section.find_all('li'):
                        req_text = li.get_text().strip()
                        if len(req_text) > 10:
                            requirements.append(req_text)
                else:
                    req_text = section.get_text().strip()
                    if len(req_text) > 20:
                        requirements.append(req_text)
        
        return requirements
    
    def extract_procedures(self, soup):
        """Extract application procedures"""
        procedures = []
        
        procedure_indicators = [
            'step', 'procedure', 'process', 'how to', 'apply',
            'submit', 'appointment', 'booking'
        ]
        
        for section in soup.find_all(['div', 'section', 'ol']):
            section_text = section.get_text().lower()
            if any(indicator in section_text for indicator in procedure_indicators):
                if section.name == 'ol':
                    steps = []
                    for li in section.find_all('li'):
                        step_text = li.get_text().strip()
                        if step_text:
                            steps.append(step_text)
                    if steps:
                        procedures.append(steps)
                else:
                    proc_text = section.get_text().strip()
                    if len(proc_text) > 20:
                        procedures.append(proc_text)
        
        return procedures
    
    def extract_fees(self, soup):
        """Extract fee information"""
        fee_patterns = [
            r'€\s*\d+(?:\.\d{2})?',
            r'\d+(?:\.\d{2})?\s*€',
            r'\$\s*\d+(?:\.\d{2})?',
            r'\d+(?:\.\d{2})?\s*USD',
            r'fee.*?\d+',
            r'cost.*?\d+',
            r'price.*?\d+'
        ]
        
        text = soup.get_text()
        fees = []
        
        for pattern in fee_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            fees.extend(matches)
        
        return list(set(fees))
    
    def extract_office_locations(self, soup):
        """Extract office/center locations"""
        locations = []
        
        location_indicators = [
            'office', 'center', 'location', 'address', 'branch'
        ]
        
        for section in soup.find_all(['div', 'section']):
            section_text = section.get_text().lower()
            if any(indicator in section_text for indicator in location_indicators):
                location_text = section.get_text().strip()
                if len(location_text) > 20:
                    locations.append(location_text)
        
        return locations
    
    def extract_working_hours(self, soup):
        """Extract working hours"""
        time_patterns = [
            r'\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?\s*-\s*\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?',
            r'\d{1,2}\s*(?:AM|PM|am|pm)\s*-\s*\d{1,2}\s*(?:AM|PM|am|pm)',
            r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday).*?\d{1,2}:\d{2}'
        ]
        
        text = soup.get_text()
        hours = []
        
        for pattern in time_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            hours.extend(matches)
        
        return list(set(hours))
    
    def extract_document_info(self, soup):
        """Extract document-related information"""
        doc_keywords = [
            'passport', 'photo', 'certificate', 'bank statement',
            'insurance', 'invitation', 'ticket', 'hotel', 'itinerary'
        ]
        
        documents = []
        text = soup.get_text().lower()
        
        for keyword in doc_keywords:
            if keyword in text:
                sentences = re.split(r'[.!?]', soup.get_text())
                for sentence in sentences:
                    if keyword in sentence.lower() and len(sentence.strip()) > 15:
                        documents.append(sentence.strip())
        
        return documents
    
    def extract_faq(self, soup):
        """Extract FAQ sections"""
        faqs = []
        
        # Look for FAQ sections
        faq_sections = soup.find_all(['div', 'section'], class_=re.compile(r'faq|question|answer', re.I))
        
        for section in faq_sections:
            questions = section.find_all(['h3', 'h4', 'h5', 'strong'])
            for question in questions:
                q_text = question.get_text().strip()
                if '?' in q_text and len(q_text) > 10:
                    # Try to find the answer (next sibling or following content)
                    answer_element = question.find_next_sibling(['p', 'div'])
                    answer = answer_element.get_text().strip() if answer_element else ""
                    
                    faqs.append({
                        'question': q_text,
                        'answer': answer
                    })
        
        return faqs
    
    def get_all_internal_links(self, start_url):
        """Get all internal links from the website"""
        try:
            self.driver.get(start_url)
            time.sleep(3)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            links = set()
            
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                full_url = urljoin(start_url, href)
                
                # Only include links from the same domain
                if self.base_url in full_url and full_url not in self.visited_urls:
                    links.add(full_url)
            
            return links
            
        except Exception as e:
            logger.error(f"Error getting links from {start_url}: {str(e)}")
            return set()
    
    def scrape_website(self, max_pages=None):
        """Main scraping function"""
        logger.info("Starting BLS Slovakia Visa website scraping...")
        
        # Start with the home page
        urls_to_visit = [self.base_url]
        visited_count = 0
        
        while urls_to_visit and (max_pages is None or visited_count < max_pages):
            current_url = urls_to_visit.pop(0)
            
            if current_url in self.visited_urls:
                continue
            
            # Extract content from current page
            page_data = self.extract_page_content(current_url)
            if page_data:
                self.scraped_data.append(page_data)
                self.visited_urls.add(current_url)
                visited_count += 1
                
                logger.info(f"Scraped page {visited_count}: {current_url}")
                
                # Get new links from this page
                new_links = self.get_all_internal_links(current_url)
                for link in new_links:
                    if link not in self.visited_urls and link not in urls_to_visit:
                        urls_to_visit.append(link)
            
            # Be respectful - add delay between requests
            time.sleep(2)
        
        logger.info(f"Scraping completed. Total pages scraped: {len(self.scraped_data)}")
        return self.scraped_data
    
    def save_data(self, filename_prefix="bls_slovakia_visa_data"):
        """Save scraped data in multiple formats"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save as JSON
        json_filename = f"{filename_prefix}_{timestamp}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(self.scraped_data, f, ensure_ascii=False, indent=2)
        
        # Save as CSV (flattened structure)
        csv_filename = f"{filename_prefix}_{timestamp}.csv"
        if self.scraped_data:
            with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
                fieldnames = self.scraped_data[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for row in self.scraped_data:
                    # Convert lists and dicts to strings for CSV
                    flattened_row = {}
                    for key, value in row.items():
                        if isinstance(value, (list, dict)):
                            flattened_row[key] = json.dumps(value, ensure_ascii=False)
                        else:
                            flattened_row[key] = value
                    writer.writerow(flattened_row)
        
        logger.info(f"Data saved as {json_filename} and {csv_filename}")
        return json_filename, csv_filename

def main():
    """Main execution function"""
    # Initialize scraper with PDF handling enabled
    scraper = BLSSlovakiaVisaScraper(headless=False, download_pdfs=True)  # Set headless=True for server mode
    
    try:
        # Scrape the website (limit to 50 pages for testing, remove limit for full scrape)
        scraped_data = scraper.scrape_website(max_pages=50)
        
        # Save the data
        saved_files = scraper.save_data()
        
        print(f"\nScraping Summary:")
        print(f"- Total web pages scraped: {len(scraped_data)}")
        print(f"- Total PDFs found: {len(scraper.pdf_data)}")
        print(f"- JSON data saved to: {saved_files['json']}")
        print(f"- Web pages CSV saved to: {saved_files['web_csv']}")
        if saved_files['pdf_csv']:
            print(f"- PDFs CSV saved to: {saved_files['pdf_csv']}")
        print(f"- Summary saved to: {saved_files['summary']}")
        print(f"- PDF files downloaded to: {saved_files['pdf_dir']}")
        
        # Display sample data
        if scraped_data:
            print(f"\nSample data from first page:")
            sample = scraped_data[0]
            print(f"Title: {sample.get('title', 'N/A')}")
            print(f"URL: {sample.get('url', 'N/A')}")
            print(f"Paragraphs found: {len(sample.get('paragraphs', []))}")
            print(f"Links found: {len(sample.get('links', []))}")
            print(f"PDF links found: {len(sample.get('pdf_links', []))}")
            print(f"Headings found: {len(sample.get('headings', []))}")
        
        # Display PDF summary
        if scraper.pdf_data:
            print(f"\nPDF Documents Found:")
            for pdf in scraper.pdf_data[:5]:  # Show first 5 PDFs
                print(f"- {pdf['filename']}")
                print(f"  Source: {pdf['source_page']}")
                print(f"  Pages: {pdf['content']['total_pages'] if pdf['content'] else 'N/A'}")
                if pdf['metadata'].get('title'):
                    print(f"  Title: {pdf['metadata']['title']}")
                print()
    
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
    except Exception as e:
        print(f"Error during scraping: {str(e)}")
        logger.exception("Full error details:")
    finally:
        # Clean up
        del scraper

if __name__ == "__main__":
    main()