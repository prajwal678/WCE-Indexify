from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import json
import logging
import re
from datetime import datetime
from indexify_extractor_sdk import Content, Extractor, ExtractorSchema
from urllib.parse import urljoin

class ExtractionSchema(BaseModel):
    type: str
    properties: Dict[str, Any]
    required: List[str] = []

class InputParams(BaseModel):
    schema: ExtractionSchema
    selector_rules: Optional[Dict[str, str]] = Field(
        default = None,
        description = "Custom CSS selector rules for extraction"
    )

class WebContentExtractor(Extractor):
    def __init__(self):
        super(WebContentExtractor, self).__init__()
        self.logger = logging.getLogger(__name__)

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text.strip())

    def _extract_date(self, text: str) -> Optional[str]:
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # ISO format
            r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
            r'\w+ \d{1,2},? \d{4}'  # Month DD, YYYY
        ] # chatgpt recco
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    date_str = match.group(0)
                    # Convert to ISO format
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    return date_obj.isoformat()
                except ValueError:
                    continue
        return None

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        images = []
        for img in soup.find_all('img'):
            src = img.get('src')
            if src:
                images.append({
                    'url': urljoin(base_url, src),
                    'alt': img.get('alt', ''),
                    'title': img.get('title', '')
                })
        return images

    def _extract_field(self, soup: BeautifulSoup, field_name: str, selector_rules: Dict[str, str], base_url: str = '') -> Any:
        selector = selector_rules.get(field_name, "")
        if not selector:
            return None

        element = soup.select_one(selector)
        if not element:
            return None

        if field_name.lower().endswith('price'):
            text = self._clean_text(element.text)
            price_match = re.search(r'[\d.,]+', text)
            if price_match:
                try:
                    return float(price_match.group().replace(',', ''))
                except ValueError:
                    return None
                    
        elif field_name.lower().endswith('date'):
            text = self._clean_text(element.text)
            return self._extract_date(text)
            
        elif field_name == 'content':
            paragraphs = element.find_all('p')
            return [self._clean_text(p.text) for p in paragraphs if self._clean_text(p.text)]
            
        elif field_name == 'images':
            return self._extract_images(element, base_url)
            
        elif field_name == 'specifications':
            specs = {}
            spec_rows = element.find_all('tr') or element.find_all('li')
            for row in spec_rows:
                key_elem = row.find('th') or row.find('strong')
                value_elem = row.find('td') or row.find(text=True, recursive=False)
                if key_elem and value_elem:
                    key = self._clean_text(key_elem.text.rstrip(':'))
                    value = self._clean_text(value_elem.text)
                    if key and value:
                        specs[key] = value
            return specs if specs else None
            
        else:
            return self._clean_text(element.text)

    def extract(self, html_content: List[Content], params: InputParams) -> List[List[Content]]:
        results = []

        # again ai recco
        default_rules = {
            "title": "h1, .title, .post-title",
            "author": ".author, .byline, .post-author",
            "publishDate": ".date, time, .published-date",
            "content": "article, .content, .post-content, .entry-content",
            "productName": "h1, .product-title",
            "price": ".price, .product-price",
            "description": ".description, .product-description",
            "specifications": ".specifications, .specs, .product-specs",
            "images": ".content img, .product-images"
        }

        selector_rules = {**default_rules, **(params.selector_rules or {})}

        for doc in html_content:
            try:
                soup = BeautifulSoup(doc.data, "html.parser")
                extracted_data = {}

                for field_name, field_schema in params.schema.properties.items():
                    value = self._extract_field(
                        soup, 
                        field_name, 
                        selector_rules,
                        base_url=doc.feature.get('url', '')
                    )
                    if value is not None:
                        extracted_data[field_name] = value

                missing_fields = [field for field in params.schema.required 
                                if field not in extracted_data]
                if missing_fields:
                    self.logger.warning(f"Missing required fields: {missing_fields}")
                    results.append([])
                    continue

                content = Content.from_text(
                    json.dumps(extracted_data),
                    feature=doc.feature
                )
                results.append([content])

            except Exception as e:
                self.logger.error(f"Error extracting content: {str(e)}")
                results.append([])

        return results

    @classmethod
    def schemas(cls) -> ExtractorSchema:
        return ExtractorSchema(
            input_params_schema={
                "type": "object",
                "properties": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "properties": {"type": "object"},
                            "required": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["type", "properties"]
                    },
                    "selector_rules": {
                        "type": "object",
                        "additionalProperties": {"type": "string"}
                    }
                },
                "required": ["schema"]
            }
        )