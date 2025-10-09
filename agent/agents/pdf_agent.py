"""
PDF Agent - Specialized processor for PDF documents
Handles: PDF files with text extraction, metadata, structure analysis, 
         image extraction, table detection, and annotation processing
"""
import os
import json
import io
import base64
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import PyPDF2
import boto3
from strands import Agent
import fitz  # PyMuPDF for advanced PDF processing
import pandas as pd
from PIL import Image
import logging

logger = logging.getLogger(__name__)

# Import error handler
try:
    from ..services.processing_error_handler import processing_error_handler
except ImportError:
    # Fallback for when not running as package
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from services.processing_error_handler import processing_error_handler


class PDFAgent:
    """Specialized agent for processing PDF documents with advanced extraction capabilities."""
    
    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self.agent = Agent()
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=region)
        self.supported_extensions = ['.pdf']
        
        # Import model configuration manager
        try:
            from ..config.model_manager import model_config_manager
            self.model_manager = model_config_manager
        except ImportError:
            # Fallback for when not running as package
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            from config.model_manager import model_config_manager
            self.model_manager = model_config_manager
        except ImportError:
            logger.warning("Model configuration manager not available, using default model")
            self.model_manager = None
    
    def can_process(self, file_path: str) -> bool:
        """Check if this agent can process the given file."""
        return file_path.lower().endswith('.pdf')

    def _resolve_file_path(self, file_path) -> str:
        """Resolve file path relative to project structure. Accepts string or Path."""
        # Convert to Path if string
        file_path_obj = Path(file_path) if isinstance(file_path, str) else file_path

        print(f"🔍 PDF Agent - Resolving file path: {file_path_obj}")
        print(f"🔍 PDF Agent - Current working directory: {Path.cwd()}")

        # If the path exists as-is, use it
        if file_path_obj.exists():
            print(f"✅ PDF Agent - Found file at original path: {file_path_obj}")
            return str(file_path_obj)

        # Try in backend directory (most common case)
        backend_path = Path("backend") / file_path_obj
        print(f"🔍 PDF Agent - Trying backend path: {backend_path}")
        if backend_path.exists():
            print(f"✅ PDF Agent - Found file at backend path: {backend_path}")
            return str(backend_path)

        # Try relative to backend directory (from agent directory)
        backend_relative_path = Path("../backend") / file_path_obj
        print(f"🔍 PDF Agent - Trying backend relative path: {backend_relative_path}")
        if backend_relative_path.exists():
            print(f"✅ PDF Agent - Found file at backend relative path: {backend_relative_path}")
            return str(backend_relative_path)

        # Try absolute path from project root
        project_root_path = Path("..") / file_path_obj
        print(f"🔍 PDF Agent - Trying project root path: {project_root_path}")
        if project_root_path.exists():
            print(f"✅ PDF Agent - Found file at project root path: {project_root_path}")
            return str(project_root_path)

        # Return original path if nothing works
        print(f"❌ PDF Agent - Could not resolve file path, using original: {file_path_obj}")
        return str(file_path_obj)

    async def process_file(self, file_path: str, user_id: str) -> Dict[str, Any]:
        """Process a PDF document file with advanced extraction capabilities."""
        try:
            print(f"📋 PDF Agent processing: {file_path}")

            # Resolve file path
            resolved_path = self._resolve_file_path(file_path)

            # Extract comprehensive PDF content
            pdf_data = await self._extract_comprehensive_content(str(resolved_path))
            
            # Analyze content with AI using optimal model
            analysis = await self._analyze_content_with_model(
                pdf_data['text'], 
                file_path, 
                pdf_data['metadata'],
                pdf_data.get('images', []),
                pdf_data.get('tables', [])
            )
            
            # Prepare enhanced result
            result = {
                "agent_type": "pdf",
                "file_path": file_path,
                "status": "completed",
                "content": {
                    "text": self._create_smart_preview(pdf_data['text'], 8000),  # Smart preview instead of truncation
                    "full_text": pdf_data['text'],
                    "structured_content": pdf_data.get('structured_content', {}),
                    "page_count": pdf_data['metadata']['page_count'],
                    "word_count": len(pdf_data['text'].split()),
                    "char_count": len(pdf_data['text']),
                    "images": pdf_data.get('images', []),
                    "tables": pdf_data.get('tables', []),
                    "annotations": pdf_data.get('annotations', [])
                },
                "analysis": analysis,
                "metadata": {
                    **pdf_data['metadata'],
                    "processed_by": "enhanced_pdf_agent",
                    "extraction_features": [
                        "text", "images", "tables", "annotations", 
                        "structure", "cross_references"
                    ]
                }
            }
            
            print(f"✅ PDF Agent completed: {file_path} ({pdf_data['metadata']['page_count']} pages, "
                  f"{len(pdf_data.get('images', []))} images, {len(pdf_data.get('tables', []))} tables)")
            return result

        except Exception as e:
            logger.error(f"PDF Agent error processing {file_path}: {e}")
            
            # Use error handler for comprehensive error reporting
            error_response = processing_error_handler.create_error_response(e, {
                "agent_type": "pdf",
                "file_path": file_path,
                "operation": "process_file"
            })
            
            # Merge with agent-specific response format
            return {
                "agent_type": "pdf",
                "file_path": file_path,
                "status": "error",
                "error": str(e),
                **error_response
            }
    
    async def _extract_comprehensive_content(self, file_path: str) -> Dict[str, Any]:
        """Extract comprehensive content including text, images, tables, and annotations."""
        try:
            # Resolve file path first
            resolved_path = self._resolve_file_path(file_path)
            print(f"📄 PDF Agent processing resolved path: {resolved_path}")
            
            # Use PyMuPDF for advanced extraction
            doc = fitz.open(resolved_path)
            
            # Initialize extraction results
            all_text = []
            all_images = []
            all_tables = []
            all_annotations = []
            structured_content = {
                "pages": [],
                "document_outline": [],
                "cross_references": {}
            }
            
            # Extract document outline/bookmarks
            outline = doc.get_toc()
            structured_content["document_outline"] = self._process_outline(outline)
            
            # Process each page
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_data = await self._extract_page_content(page, page_num + 1)
                
                # Collect page text
                if page_data['text']:
                    all_text.append(f"--- Page {page_num + 1} ---\n{page_data['text']}")
                
                # Collect images
                all_images.extend(page_data['images'])
                
                # Collect tables
                all_tables.extend(page_data['tables'])
                
                # Collect annotations
                all_annotations.extend(page_data['annotations'])
                
                # Store structured page data
                structured_content["pages"].append({
                    "page_number": page_num + 1,
                    "text_blocks": page_data.get('text_blocks', []),
                    "image_count": len(page_data['images']),
                    "table_count": len(page_data['tables']),
                    "annotation_count": len(page_data['annotations'])
                })
            
            # Extract metadata
            metadata = self._extract_enhanced_metadata(doc, file_path)
            
            # Detect cross-references and correlate content
            structured_content["cross_references"] = self._detect_cross_references(all_text)
            structured_content["content_correlation"] = await self._correlate_cross_page_content(
                structured_content["pages"], all_text, all_images, all_tables
            )
            structured_content["navigation_structure"] = self._extract_navigation_structure(
                structured_content["document_outline"], structured_content["pages"]
            )
            
            doc.close()
            
            return {
                "text": '\n\n'.join(all_text),
                "images": all_images,
                "tables": all_tables,
                "annotations": all_annotations,
                "structured_content": structured_content,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Error in comprehensive PDF extraction for {file_path}: {e}")
            # Fallback to basic extraction
            return await self._extract_pdf_content_fallback(file_path)
    
    async def _extract_pdf_content_fallback(self, file_path: str) -> Dict[str, Any]:
        """Extract text content and metadata from PDF."""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extract metadata
                metadata = {
                    "page_count": len(pdf_reader.pages),
                    "file_size": os.path.getsize(file_path),
                    "file_type": ".pdf"
                }
                
                # Try to get PDF metadata
                if pdf_reader.metadata:
                    metadata.update({
                        "title": pdf_reader.metadata.get('/Title', ''),
                        "author": pdf_reader.metadata.get('/Author', ''),
                        "subject": pdf_reader.metadata.get('/Subject', ''),
                        "creator": pdf_reader.metadata.get('/Creator', ''),
                        "producer": pdf_reader.metadata.get('/Producer', ''),
                        "creation_date": str(pdf_reader.metadata.get('/CreationDate', '')),
                        "modification_date": str(pdf_reader.metadata.get('/ModDate', ''))
                    })
                
                # Extract text from all pages
                text_content = []
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text.strip():
                            text_content.append(f"--- Page {page_num + 1} ---\n{page_text}")
                    except Exception as e:
                        print(f"⚠️ Error extracting text from page {page_num + 1}: {e}")
                        text_content.append(f"--- Page {page_num + 1} ---\n[Text extraction failed]")
                
                full_text = '\n\n'.join(text_content)
                
                return {
                    "text": full_text,
                    "metadata": metadata,
                    "images": [],
                    "tables": [],
                    "annotations": [],
                    "structured_content": {}
                }
                
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {e}")
            return {
                "text": f"Error processing PDF: {str(e)}",
                "metadata": {
                    "page_count": 0,
                    "file_size": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                    "file_type": ".pdf",
                    "error": str(e)
                },
                "images": [],
                "tables": [],
                "annotations": [],
                "structured_content": {}
            }
    
    async def _extract_page_content(self, page, page_num: int) -> Dict[str, Any]:
        """Extract comprehensive content from a single PDF page."""
        try:
            page_data = {
                "text": "",
                "text_blocks": [],
                "images": [],
                "tables": [],
                "annotations": []
            }
            
            # Extract text with structure
            text_dict = page.get_text("dict")
            page_text, text_blocks = self._process_text_structure(text_dict, page_num)
            page_data["text"] = page_text
            page_data["text_blocks"] = text_blocks
            
            # Extract images
            page_data["images"] = await self._extract_page_images(page, page_num)
            
            # Extract tables
            page_data["tables"] = self._extract_page_tables(page, page_num)
            
            # Extract annotations
            page_data["annotations"] = self._extract_page_annotations(page, page_num)
            
            return page_data
            
        except Exception as e:
            logger.error(f"Error extracting content from page {page_num}: {e}")
            return {
                "text": page.get_text() if hasattr(page, 'get_text') else "",
                "text_blocks": [],
                "images": [],
                "tables": [],
                "annotations": []
            }
    
    def _process_text_structure(self, text_dict: Dict, page_num: int) -> Tuple[str, List[Dict]]:
        """Process text structure to preserve formatting and hierarchy."""
        text_blocks = []
        page_text = []
        
        try:
            for block in text_dict.get("blocks", []):
                if "lines" in block:  # Text block
                    block_text = []
                    block_info = {
                        "type": "text",
                        "page": page_num,
                        "bbox": block.get("bbox", []),
                        "content": "",
                        "font_info": []
                    }
                    
                    for line in block["lines"]:
                        line_text = []
                        for span in line.get("spans", []):
                            span_text = span.get("text", "").strip()
                            if span_text:
                                line_text.append(span_text)
                                
                                # Collect font information
                                font_info = {
                                    "font": span.get("font", ""),
                                    "size": span.get("size", 0),
                                    "flags": span.get("flags", 0),
                                    "color": span.get("color", 0)
                                }
                                block_info["font_info"].append(font_info)
                        
                        if line_text:
                            block_text.append(" ".join(line_text))
                    
                    if block_text:
                        block_content = "\n".join(block_text)
                        block_info["content"] = block_content
                        text_blocks.append(block_info)
                        page_text.append(block_content)
            
            return "\n\n".join(page_text), text_blocks
            
        except Exception as e:
            logger.error(f"Error processing text structure for page {page_num}: {e}")
            return "", []
    
    async def _extract_page_images(self, page, page_num: int) -> List[Dict[str, Any]]:
        """Extract images and diagrams from a PDF page."""
        images = []
        
        try:
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                try:
                    # Get image data
                    xref = img[0]
                    pix = fitz.Pixmap(page.parent, xref)
                    
                    # Convert to PIL Image for processing
                    if pix.n - pix.alpha < 4:  # GRAY or RGB
                        img_data = pix.tobytes("png")
                        pil_image = Image.open(io.BytesIO(img_data))
                        
                        # Convert to base64 for storage
                        buffered = io.BytesIO()
                        pil_image.save(buffered, format="PNG")
                        img_base64 = base64.b64encode(buffered.getvalue()).decode()
                        
                        # Get image position on page
                        img_rects = page.get_image_rects(xref)
                        bbox = img_rects[0] if img_rects else [0, 0, 0, 0]
                        
                        image_info = {
                            "page": page_num,
                            "index": img_index,
                            "xref": xref,
                            "bbox": list(bbox),
                            "width": pil_image.width,
                            "height": pil_image.height,
                            "format": "PNG",
                            "data": img_base64,
                            "size_bytes": len(img_data)
                        }
                        
                        images.append(image_info)
                    
                    pix = None  # Clean up
                    
                except Exception as e:
                    logger.error(f"Error extracting image {img_index} from page {page_num}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error extracting images from page {page_num}: {e}")
        
        return images
    
    def _extract_page_tables(self, page, page_num: int) -> List[Dict[str, Any]]:
        """Extract table structures from a PDF page."""
        tables = []
        
        try:
            # Use PyMuPDF's table detection
            tabs = page.find_tables()
            
            for tab_index, tab in enumerate(tabs):
                try:
                    # Extract table data
                    table_data = tab.extract()
                    
                    if table_data:
                        # Convert to pandas DataFrame for structure analysis
                        df = pd.DataFrame(table_data[1:], columns=table_data[0] if table_data else [])
                        
                        table_info = {
                            "page": page_num,
                            "index": tab_index,
                            "bbox": list(tab.bbox),
                            "rows": len(table_data),
                            "columns": len(table_data[0]) if table_data else 0,
                            "data": table_data,
                            "structured_data": df.to_dict('records') if not df.empty else [],
                            "headers": table_data[0] if table_data else [],
                            "confidence": getattr(tab, 'confidence', 0.8)  # Default confidence
                        }
                        
                        tables.append(table_info)
                
                except Exception as e:
                    logger.error(f"Error processing table {tab_index} on page {page_num}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error extracting tables from page {page_num}: {e}")
        
        return tables
    
    def _extract_page_annotations(self, page, page_num: int) -> List[Dict[str, Any]]:
        """Extract annotations and comments from a PDF page."""
        annotations = []
        
        try:
            for annot in page.annots():
                try:
                    annot_dict = annot.info
                    
                    annotation_info = {
                        "page": page_num,
                        "type": annot_dict.get("type", ""),
                        "content": annot_dict.get("content", ""),
                        "author": annot_dict.get("title", ""),
                        "subject": annot_dict.get("subject", ""),
                        "bbox": list(annot.rect),
                        "creation_date": annot_dict.get("creationDate", ""),
                        "modification_date": annot_dict.get("modDate", ""),
                        "color": annot_dict.get("color", []),
                        "opacity": annot_dict.get("opacity", 1.0)
                    }
                    
                    # Extract annotation text if available
                    if hasattr(annot, 'get_text'):
                        annotation_info["text"] = annot.get_text()
                    
                    annotations.append(annotation_info)
                
                except Exception as e:
                    logger.error(f"Error processing annotation on page {page_num}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error extracting annotations from page {page_num}: {e}")
        
        return annotations
    
    def _process_outline(self, outline: List) -> List[Dict[str, Any]]:
        """Process document outline/bookmarks into structured format."""
        processed_outline = []
        
        try:
            for item in outline:
                if len(item) >= 3:
                    outline_item = {
                        "level": item[0],
                        "title": item[1],
                        "page": item[2],
                        "children": []
                    }
                    processed_outline.append(outline_item)
        
        except Exception as e:
            logger.error(f"Error processing document outline: {e}")
        
        return processed_outline
    
    def _extract_enhanced_metadata(self, doc, file_path: str) -> Dict[str, Any]:
        """Extract comprehensive metadata from PDF document."""
        try:
            metadata = {
                "page_count": len(doc),
                "file_size": os.path.getsize(file_path),
                "file_type": ".pdf"
            }
            
            # Get document metadata
            doc_metadata = doc.metadata
            if doc_metadata:
                metadata.update({
                    "title": doc_metadata.get("title", ""),
                    "author": doc_metadata.get("author", ""),
                    "subject": doc_metadata.get("subject", ""),
                    "creator": doc_metadata.get("creator", ""),
                    "producer": doc_metadata.get("producer", ""),
                    "creation_date": doc_metadata.get("creationDate", ""),
                    "modification_date": doc_metadata.get("modDate", ""),
                    "keywords": doc_metadata.get("keywords", "")
                })
            
            # Add document structure information
            metadata.update({
                "has_outline": len(doc.get_toc()) > 0,
                "is_encrypted": doc.needs_pass,
                "page_mode": doc.page_mode if hasattr(doc, 'page_mode') else ""
                # Removed 'layout' field as it's a bound method that can't be serialized
            })
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting enhanced metadata: {e}")
            return {
                "page_count": 0,
                "file_size": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                "file_type": ".pdf",
                "error": str(e)
            }
    
    def _detect_cross_references(self, text_pages: List[str]) -> Dict[str, List[str]]:
        """Detect cross-references between pages and sections."""
        cross_refs = {
            "figures": [],
            "tables": [],
            "sections": [],
            "pages": []
        }
        
        try:
            import re
            
            full_text = " ".join(text_pages)
            
            # Detect figure references
            fig_refs = re.findall(r'(?:Figure|Fig\.?)\s+(\d+(?:\.\d+)?)', full_text, re.IGNORECASE)
            cross_refs["figures"] = list(set(fig_refs))
            
            # Detect table references
            table_refs = re.findall(r'(?:Table|Tbl\.?)\s+(\d+(?:\.\d+)?)', full_text, re.IGNORECASE)
            cross_refs["tables"] = list(set(table_refs))
            
            # Detect section references
            section_refs = re.findall(r'(?:Section|Sec\.?)\s+(\d+(?:\.\d+)?)', full_text, re.IGNORECASE)
            cross_refs["sections"] = list(set(section_refs))
            
            # Detect page references
            page_refs = re.findall(r'(?:page|p\.?)\s+(\d+)', full_text, re.IGNORECASE)
            cross_refs["pages"] = list(set(page_refs))
            
        except Exception as e:
            logger.error(f"Error detecting cross-references: {e}")
        
        return cross_refs
    
    async def _analyze_content_with_model(self, content: str, file_path: str, 
                                         metadata: Dict[str, Any], images: List[Dict], 
                                         tables: List[Dict]) -> Dict[str, Any]:
        """Analyze PDF content using optimal model from model manager."""
        try:
            # Get optimal model for PDF processing
            model_spec = None
            if self.model_manager:
                model_spec = self.model_manager.get_model_for_agent("pdf", "text")
            
            # Use model-specific configuration or fallback to default
            model_id = model_spec.model_id if model_spec else os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-sonnet-20241022-v2:0")
            max_tokens = model_spec.max_tokens if model_spec else 2000
            temperature = model_spec.temperature if model_spec else 0.1
            
            # Create enhanced prompt with extracted content information
            prompt = f"""
Analyze this PDF document comprehensively:

File: {Path(file_path).name}
Pages: {metadata.get('page_count', 'Unknown')}
Title: {metadata.get('title', 'Not specified')}
Author: {metadata.get('author', 'Not specified')}
Images extracted: {len(images)}
Tables extracted: {len(tables)}
Has outline: {metadata.get('has_outline', False)}

Content Preview: {content[:3000]}...

{"Table summaries:" if tables else ""}
{self._summarize_tables(tables[:3]) if tables else ""}

Please provide a comprehensive analysis including:
1. Document type and classification
2. Main topics, themes, and subject matter
3. Key concepts, terminology, and definitions
4. Document structure and organization
5. Educational content assessment:
   - Target audience and difficulty level
   - Learning objectives and outcomes
   - Prerequisites and background knowledge
   - Cognitive complexity (Bloom's taxonomy levels)
6. Content quality indicators:
   - Clarity and coherence
   - Depth of coverage
   - Use of examples and illustrations
7. Notable structural elements:
   - Tables and their content types
   - Images and diagrams
   - Cross-references and citations
8. Summary and key takeaways (3-4 sentences)

Format as structured JSON with clear categories and confidence scores where applicable.
"""
            
            response = self.bedrock_client.invoke_model(
                modelId=model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            result = json.loads(response['body'].read())
            analysis_text = result['content'][0]['text']
            
            return {
                "ai_analysis": analysis_text,
                "content_type": "enhanced_pdf_document",
                "processing_method": "advanced_pdf_extraction_and_ai_analysis",
                "model_used": model_id,
                "pages_processed": metadata.get('page_count', 0),
                "images_extracted": len(images),
                "tables_extracted": len(tables),
                "extraction_confidence": self._calculate_extraction_confidence(metadata, images, tables)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing PDF content with model: {e}")
            
            # Handle throttling errors specially
            if "throttling" in str(e).lower() or "too many requests" in str(e).lower():
                return {
                    "ai_analysis": "AI analysis temporarily unavailable due to rate limiting. Content extraction completed successfully.",
                    "content_type": "enhanced_pdf_document",
                    "processing_method": "advanced_pdf_extraction_without_ai_analysis",
                    "model_used": model_id,
                    "pages_processed": metadata.get('page_count', 0),
                    "images_extracted": len(images),
                    "tables_extracted": len(tables),
                    "extraction_confidence": self._calculate_extraction_confidence(metadata, images, tables),
                    "throttling_notice": "AI analysis skipped due to AWS Bedrock throttling - content extraction completed successfully",
                    "retry_recommendation": "Wait 60 seconds and try again for AI analysis"
                }
            
            # For other errors, try fallback analysis
            return await self._analyze_content_fallback(content, file_path, metadata)
    
    def _summarize_tables(self, tables: List[Dict]) -> str:
        """Create a summary of extracted tables for analysis."""
        try:
            summaries = []
            for i, table in enumerate(tables):
                # Safely get headers and filter out None values
                headers = table.get('headers', []) or []
                # Filter out None values and convert to strings
                valid_headers = [str(h) for h in headers if h is not None][:3]
                headers_str = ', '.join(valid_headers) if valid_headers else 'No headers'

                page = table.get('page', 'Unknown')
                rows = table.get('rows', '?')
                columns = table.get('columns', '?')

                summary = f"Table {i+1} (Page {page}): {rows}x{columns} - Headers: {headers_str}"
                summaries.append(summary)

            return '\n'.join(summaries) if summaries else "No table summaries available"
        except Exception as e:
            logger.error(f"Error summarizing tables: {e}")
            return "Table summary unavailable"
    
    def _calculate_extraction_confidence(self, metadata: Dict, images: List, tables: List) -> float:
        """Calculate confidence score for extraction quality."""
        confidence = 0.7  # Base confidence
        
        # Boost confidence based on successful extractions
        if metadata.get('page_count', 0) > 0:
            confidence += 0.1
        if images:
            confidence += 0.1
        if tables:
            confidence += 0.1
        if metadata.get('has_outline', False):
            confidence += 0.05
        if not metadata.get('error'):
            confidence += 0.05
        
        return min(confidence, 1.0)
    
    async def _analyze_content_fallback(self, content: str, file_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback PDF content analysis using basic AI."""
        try:
            prompt = f"""
Analyze this PDF document and provide insights:

File: {Path(file_path).name}
Pages: {metadata.get('page_count', 'Unknown')}
Title: {metadata.get('title', 'Not specified')}
Author: {metadata.get('author', 'Not specified')}

Content Preview: {self._create_smart_preview(content, 3000)}...

Please provide:
1. Document type (academic paper, manual, report, book, etc.)
2. Main topics and themes
3. Key concepts and terminology
4. Document structure and organization
5. Target audience and difficulty level
6. Learning objectives (if educational)
7. Summary in 2-3 sentences
8. Notable features (tables, figures, references, etc.)

Format as JSON with clear categories.
"""
            
            response = self.bedrock_client.invoke_model(
                modelId=os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-sonnet-20241022-v2:0"),
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1200,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            result = json.loads(response['body'].read())
            analysis_text = result['content'][0]['text']
            
            return {
                "ai_analysis": analysis_text,
                "content_type": "pdf_document",
                "processing_method": "fallback_pdf_analysis",
                "pages_processed": metadata.get('page_count', 0)
            }
            
        except Exception as e:
            logger.error(f"Error in fallback PDF analysis: {e}")
            return {
                "ai_analysis": f"Analysis failed: {str(e)}",
                "content_type": "pdf_document",
                "processing_method": "pdf_text_extraction_only",
                "pages_processed": metadata.get('page_count', 0)
            }
    
    async def _correlate_cross_page_content(self, pages: List[Dict], text_pages: List[str], 
                                          images: List[Dict], tables: List[Dict]) -> Dict[str, Any]:
        """Correlate content across multiple PDF pages to identify relationships."""
        correlation_data = {
            "figure_references": {},
            "table_references": {},
            "section_references": {},
            "content_flow": [],
            "topic_continuity": [],
            "cross_page_relationships": []
        }
        
        try:
            # Resolve figure references
            correlation_data["figure_references"] = self._resolve_figure_references(text_pages, images)
            
            # Resolve table references
            correlation_data["table_references"] = self._resolve_table_references(text_pages, tables)
            
            # Resolve section references
            correlation_data["section_references"] = self._resolve_section_references(text_pages, pages)
            
            # Analyze content flow between pages
            correlation_data["content_flow"] = self._analyze_content_flow(text_pages)
            
            # Detect topic continuity across pages
            correlation_data["topic_continuity"] = await self._detect_topic_continuity(text_pages)
            
            # Identify cross-page relationships
            correlation_data["cross_page_relationships"] = self._identify_cross_page_relationships(
                pages, images, tables
            )
            
        except Exception as e:
            logger.error(f"Error correlating cross-page content: {e}")
        
        return correlation_data
    
    def _resolve_figure_references(self, text_pages: List[str], images: List[Dict]) -> Dict[str, Any]:
        """Resolve figure references to actual images in the document."""
        import re
        
        figure_refs = {}
        
        try:
            # Create mapping of images by page
            images_by_page = {}
            for img in images:
                page_num = img['page']
                if page_num not in images_by_page:
                    images_by_page[page_num] = []
                images_by_page[page_num].append(img)
            
            # Find figure references in text
            for page_idx, page_text in enumerate(text_pages):
                page_num = page_idx + 1
                
                # Find all figure references on this page
                fig_matches = re.finditer(r'(?:Figure|Fig\.?)\s+(\d+(?:\.\d+)?)', page_text, re.IGNORECASE)
                
                for match in fig_matches:
                    fig_number = match.group(1)
                    ref_position = match.start()
                    
                    # Try to find corresponding image
                    resolved_image = self._find_corresponding_image(
                        fig_number, page_num, images_by_page, text_pages
                    )
                    
                    if fig_number not in figure_refs:
                        figure_refs[fig_number] = {
                            "references": [],
                            "resolved_image": resolved_image,
                            "confidence": 0.0
                        }
                    
                    figure_refs[fig_number]["references"].append({
                        "page": page_num,
                        "position": ref_position,
                        "context": page_text[max(0, ref_position-100):ref_position+100]
                    })
                    
                    # Calculate confidence based on proximity and context
                    if resolved_image:
                        confidence = self._calculate_reference_confidence(
                            page_num, resolved_image['page'], match.group(0), page_text
                        )
                        figure_refs[fig_number]["confidence"] = max(
                            figure_refs[fig_number]["confidence"], confidence
                        )
        
        except Exception as e:
            logger.error(f"Error resolving figure references: {e}")
        
        return figure_refs
    
    def _resolve_table_references(self, text_pages: List[str], tables: List[Dict]) -> Dict[str, Any]:
        """Resolve table references to actual tables in the document."""
        import re
        
        table_refs = {}
        
        try:
            # Create mapping of tables by page
            tables_by_page = {}
            for table in tables:
                page_num = table['page']
                if page_num not in tables_by_page:
                    tables_by_page[page_num] = []
                tables_by_page[page_num].append(table)
            
            # Find table references in text
            for page_idx, page_text in enumerate(text_pages):
                page_num = page_idx + 1
                
                # Find all table references on this page
                table_matches = re.finditer(r'(?:Table|Tbl\.?)\s+(\d+(?:\.\d+)?)', page_text, re.IGNORECASE)
                
                for match in table_matches:
                    table_number = match.group(1)
                    ref_position = match.start()
                    
                    # Try to find corresponding table
                    resolved_table = self._find_corresponding_table(
                        table_number, page_num, tables_by_page, text_pages
                    )
                    
                    if table_number not in table_refs:
                        table_refs[table_number] = {
                            "references": [],
                            "resolved_table": resolved_table,
                            "confidence": 0.0
                        }
                    
                    table_refs[table_number]["references"].append({
                        "page": page_num,
                        "position": ref_position,
                        "context": page_text[max(0, ref_position-100):ref_position+100]
                    })
                    
                    # Calculate confidence
                    if resolved_table:
                        confidence = self._calculate_reference_confidence(
                            page_num, resolved_table['page'], match.group(0), page_text
                        )
                        table_refs[table_number]["confidence"] = max(
                            table_refs[table_number]["confidence"], confidence
                        )
        
        except Exception as e:
            logger.error(f"Error resolving table references: {e}")
        
        return table_refs
    
    def _resolve_section_references(self, text_pages: List[str], pages: List[Dict]) -> Dict[str, Any]:
        """Resolve section references to actual sections in the document."""
        import re
        
        section_refs = {}
        
        try:
            # Extract section headings from pages
            section_headings = self._extract_section_headings(pages)
            
            # Find section references in text
            for page_idx, page_text in enumerate(text_pages):
                page_num = page_idx + 1
                
                # Find section references
                section_matches = re.finditer(
                    r'(?:Section|Sec\.?|Chapter|Ch\.?)\s+(\d+(?:\.\d+)?)', 
                    page_text, re.IGNORECASE
                )
                
                for match in section_matches:
                    section_number = match.group(1)
                    ref_position = match.start()
                    
                    # Try to find corresponding section
                    resolved_section = self._find_corresponding_section(
                        section_number, section_headings
                    )
                    
                    if section_number not in section_refs:
                        section_refs[section_number] = {
                            "references": [],
                            "resolved_section": resolved_section,
                            "confidence": 0.0
                        }
                    
                    section_refs[section_number]["references"].append({
                        "page": page_num,
                        "position": ref_position,
                        "context": page_text[max(0, ref_position-100):ref_position+100]
                    })
                    
                    # Calculate confidence
                    if resolved_section:
                        confidence = 0.8  # High confidence for section references
                        section_refs[section_number]["confidence"] = max(
                            section_refs[section_number]["confidence"], confidence
                        )
        
        except Exception as e:
            logger.error(f"Error resolving section references: {e}")
        
        return section_refs
    
    def _analyze_content_flow(self, text_pages: List[str]) -> List[Dict[str, Any]]:
        """Analyze how content flows between pages."""
        content_flow = []
        
        try:
            for i in range(len(text_pages) - 1):
                current_page = text_pages[i]
                next_page = text_pages[i + 1]
                
                # Analyze sentence continuity
                current_sentences = current_page.split('.')[-3:]  # Last 3 sentences
                next_sentences = next_page.split('.')[:3]  # First 3 sentences
                
                # Check for continuation indicators
                continuation_score = self._calculate_continuation_score(
                    current_sentences, next_sentences
                )
                
                flow_info = {
                    "from_page": i + 1,
                    "to_page": i + 2,
                    "continuation_score": continuation_score,
                    "flow_type": self._determine_flow_type(continuation_score),
                    "transition_indicators": self._find_transition_indicators(
                        current_page[-200:], next_page[:200]
                    )
                }
                
                content_flow.append(flow_info)
        
        except Exception as e:
            logger.error(f"Error analyzing content flow: {e}")
        
        return content_flow
    
    async def _detect_topic_continuity(self, text_pages: List[str]) -> List[Dict[str, Any]]:
        """Detect topic continuity and changes across pages."""
        topic_continuity = []
        
        try:
            # Simple keyword-based topic detection
            for i in range(len(text_pages)):
                page_text = text_pages[i]
                
                # Extract key terms from page
                key_terms = self._extract_key_terms(page_text)
                
                topic_info = {
                    "page": i + 1,
                    "key_terms": key_terms,
                    "topic_similarity": 0.0,
                    "topic_change": False
                }
                
                # Compare with previous page
                if i > 0:
                    prev_terms = topic_continuity[i-1]["key_terms"]
                    similarity = self._calculate_term_similarity(key_terms, prev_terms)
                    topic_info["topic_similarity"] = similarity
                    topic_info["topic_change"] = similarity < 0.3  # Threshold for topic change
                
                topic_continuity.append(topic_info)
        
        except Exception as e:
            logger.error(f"Error detecting topic continuity: {e}")
        
        return topic_continuity
    
    def _identify_cross_page_relationships(self, pages: List[Dict], images: List[Dict], 
                                         tables: List[Dict]) -> List[Dict[str, Any]]:
        """Identify relationships between content elements across pages."""
        relationships = []
        
        try:
            # Group content by type and page
            content_by_page = {}
            for page_info in pages:
                page_num = page_info["page_number"]
                content_by_page[page_num] = {
                    "images": [img for img in images if img["page"] == page_num],
                    "tables": [tbl for tbl in tables if tbl["page"] == page_num],
                    "text_blocks": page_info.get("text_blocks", [])
                }
            
            # Find relationships between adjacent pages
            for page_num in range(1, len(pages)):
                current_page = content_by_page.get(page_num, {})
                next_page = content_by_page.get(page_num + 1, {})
                
                # Check for split tables
                split_table_rel = self._check_split_tables(
                    current_page.get("tables", []), 
                    next_page.get("tables", [])
                )
                if split_table_rel:
                    relationships.append(split_table_rel)
                
                # Check for continued figures/diagrams
                figure_continuation = self._check_figure_continuation(
                    current_page.get("images", []), 
                    next_page.get("images", [])
                )
                if figure_continuation:
                    relationships.append(figure_continuation)
        
        except Exception as e:
            logger.error(f"Error identifying cross-page relationships: {e}")
        
        return relationships
    
    def _extract_navigation_structure(self, outline: List[Dict], pages: List[Dict]) -> Dict[str, Any]:
        """Extract document navigation structure from outline and page content."""
        navigation = {
            "outline_structure": outline,
            "page_hierarchy": [],
            "navigation_links": []
        }
        
        try:
            # Create page hierarchy based on outline
            for page_info in pages:
                page_num = page_info["page_number"]
                
                # Find outline items that point to this page
                outline_items = [
                    item for item in outline 
                    if item.get("page") == page_num
                ]
                
                hierarchy_info = {
                    "page": page_num,
                    "outline_items": outline_items,
                    "section_level": min([item.get("level", 999) for item in outline_items]) if outline_items else 999,
                    "is_section_start": len(outline_items) > 0
                }
                
                navigation["page_hierarchy"].append(hierarchy_info)
            
            # Create navigation links
            navigation["navigation_links"] = self._create_navigation_links(outline)
        
        except Exception as e:
            logger.error(f"Error extracting navigation structure: {e}")
        
        return navigation
    
    # Helper methods for cross-page correlation
    
    def _find_corresponding_image(self, fig_number: str, ref_page: int, 
                                images_by_page: Dict, text_pages: List[str]) -> Optional[Dict]:
        """Find the image that corresponds to a figure reference."""
        # Look for image on same page first
        if ref_page in images_by_page:
            return images_by_page[ref_page][0] if images_by_page[ref_page] else None
        
        # Look on adjacent pages
        for page_offset in [-1, 1, -2, 2]:
            check_page = ref_page + page_offset
            if check_page in images_by_page and images_by_page[check_page]:
                return images_by_page[check_page][0]
        
        return None
    
    def _find_corresponding_table(self, table_number: str, ref_page: int, 
                                tables_by_page: Dict, text_pages: List[str]) -> Optional[Dict]:
        """Find the table that corresponds to a table reference."""
        # Look for table on same page first
        if ref_page in tables_by_page:
            return tables_by_page[ref_page][0] if tables_by_page[ref_page] else None
        
        # Look on adjacent pages
        for page_offset in [-1, 1, -2, 2]:
            check_page = ref_page + page_offset
            if check_page in tables_by_page and tables_by_page[check_page]:
                return tables_by_page[check_page][0]
        
        return None
    
    def _find_corresponding_section(self, section_number: str, 
                                  section_headings: List[Dict]) -> Optional[Dict]:
        """Find the section that corresponds to a section reference."""
        for section in section_headings:
            if section.get("number") == section_number:
                return section
        return None
    
    def _extract_section_headings(self, pages: List[Dict]) -> List[Dict]:
        """Extract section headings from page content."""
        import re
        
        headings = []
        
        for page_info in pages:
            text_blocks = page_info.get("text_blocks", [])
            
            for block in text_blocks:
                content = block.get("content", "")
                
                # Look for numbered headings
                heading_match = re.match(r'^(\d+(?:\.\d+)*)\s+(.+)$', content.strip())
                if heading_match:
                    headings.append({
                        "number": heading_match.group(1),
                        "title": heading_match.group(2),
                        "page": page_info["page_number"],
                        "level": len(heading_match.group(1).split('.'))
                    })
        
        return headings
    
    def _calculate_reference_confidence(self, ref_page: int, target_page: int, 
                                      ref_text: str, context: str) -> float:
        """Calculate confidence score for a reference resolution."""
        confidence = 0.5  # Base confidence
        
        # Same page = high confidence
        if ref_page == target_page:
            confidence += 0.4
        # Adjacent page = medium confidence
        elif abs(ref_page - target_page) == 1:
            confidence += 0.2
        # Nearby pages = lower confidence
        elif abs(ref_page - target_page) <= 3:
            confidence += 0.1
        
        # Check for contextual indicators
        if any(word in context.lower() for word in ['above', 'below', 'following', 'preceding']):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _calculate_continuation_score(self, current_sentences: List[str], 
                                    next_sentences: List[str]) -> float:
        """Calculate how likely content continues from one page to the next."""
        score = 0.0
        
        if not current_sentences or not next_sentences:
            return score
        
        # Check for incomplete sentences
        last_sentence = current_sentences[-1].strip()
        if not last_sentence.endswith(('.', '!', '?')):
            score += 0.5
        
        # Check for continuation words
        first_sentence = next_sentences[0].strip().lower()
        continuation_words = ['however', 'therefore', 'furthermore', 'moreover', 'additionally']
        if any(first_sentence.startswith(word) for word in continuation_words):
            score += 0.3
        
        return min(score, 1.0)
    
    def _determine_flow_type(self, continuation_score: float) -> str:
        """Determine the type of content flow between pages."""
        if continuation_score > 0.7:
            return "strong_continuation"
        elif continuation_score > 0.3:
            return "weak_continuation"
        else:
            return "new_section"
    
    def _find_transition_indicators(self, page_end: str, page_start: str) -> List[str]:
        """Find indicators of content transition between pages."""
        indicators = []
        
        # Check for common transition phrases
        transition_phrases = [
            'continued on next page', 'see next page', 'table continues',
            'figure continues', 'to be continued'
        ]
        
        combined_text = (page_end + " " + page_start).lower()
        for phrase in transition_phrases:
            if phrase in combined_text:
                indicators.append(phrase)
        
        return indicators
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract key terms from text for topic analysis."""
        import re
        
        # Simple keyword extraction (could be enhanced with NLP)
        words = re.findall(r'\b[A-Za-z]{4,}\b', text.lower())
        
        # Filter common words
        stop_words = {'this', 'that', 'with', 'have', 'will', 'from', 'they', 'been', 'were', 'said'}
        key_terms = [word for word in words if word not in stop_words]
        
        # Return most frequent terms
        from collections import Counter
        term_counts = Counter(key_terms)
        return [term for term, count in term_counts.most_common(10)]
    
    def _calculate_term_similarity(self, terms1: List[str], terms2: List[str]) -> float:
        """Calculate similarity between two sets of terms."""
        if not terms1 or not terms2:
            return 0.0
        
        set1, set2 = set(terms1), set(terms2)
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def _check_split_tables(self, current_tables: List[Dict], 
                          next_tables: List[Dict]) -> Optional[Dict]:
        """Check if tables are split across pages."""
        if not current_tables or not next_tables:
            return None
        
        # Simple heuristic: similar column structure
        for curr_table in current_tables:
            for next_table in next_tables:
                if (curr_table.get('columns') == next_table.get('columns') and
                    curr_table.get('headers') == next_table.get('headers')):
                    return {
                        "type": "split_table",
                        "from_page": curr_table['page'],
                        "to_page": next_table['page'],
                        "confidence": 0.8
                    }
        
        return None
    
    def _check_figure_continuation(self, current_images: List[Dict], 
                                 next_images: List[Dict]) -> Optional[Dict]:
        """Check if figures continue across pages."""
        if not current_images or not next_images:
            return None
        
        # Simple heuristic: similar image sizes
        for curr_img in current_images:
            for next_img in next_images:
                size_diff = abs(curr_img.get('width', 0) - next_img.get('width', 0))
                if size_diff < 50:  # Similar width
                    return {
                        "type": "figure_continuation",
                        "from_page": curr_img['page'],
                        "to_page": next_img['page'],
                        "confidence": 0.6
                    }
        
        return None
    
    def _create_navigation_links(self, outline: List[Dict]) -> List[Dict]:
        """Create navigation links from document outline."""
        links = []
        
        for i, item in enumerate(outline):
            link = {
                "from_item": item,
                "next_item": outline[i + 1] if i + 1 < len(outline) else None,
                "prev_item": outline[i - 1] if i > 0 else None,
                "parent_item": None,  # Could be enhanced to detect hierarchy
                "children": []  # Could be enhanced to detect hierarchy
            }
            links.append(link)
        
        return links


    def _create_smart_preview(self, content: str, max_length: int = 8000) -> str:
        """Create a smart preview that preserves important content instead of simple truncation."""
        if len(content) <= max_length:
            return content
        
        # Split content into paragraphs
        paragraphs = content.split('\n\n')
        
        # Prioritize paragraphs that contain important information
        important_paragraphs = []
        regular_paragraphs = []
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # Check if paragraph contains important keywords or patterns
            if (any(keyword in para.lower() for keyword in 
                   ['abstract', 'introduction', 'conclusion', 'summary', 'important', 'key', 
                    'definition', 'overview', 'objective', 'goal', 'purpose', 'main', 'primary', 
                    'essential', 'figure', 'table', 'chapter', 'section']) or
                para.startswith('#') or  # Headings
                ':' in para[:100] or  # Likely definitions or key points
                len(para.split()) < 50):  # Short paragraphs are often important
                important_paragraphs.append(para)
            else:
                regular_paragraphs.append(para)
        
        # Build preview starting with important paragraphs
        preview_parts = []
        current_length = 0
        
        # Add important paragraphs first
        for para in important_paragraphs:
            if current_length + len(para) > max_length:
                break
            preview_parts.append(para)
            current_length += len(para) + 2  # +2 for \n\n
        
        # Add regular paragraphs until we reach the limit
        for para in regular_paragraphs:
            if current_length + len(para) > max_length:
                break
            preview_parts.append(para)
            current_length += len(para) + 2
        
        # If we still have space, add a truncation indicator
        result = '\n\n'.join(preview_parts)
        if len(content) > len(result):
            result += f"\n\n[Content continues... {len(content) - len(result)} more characters]"
        
        return result


# Global instance
pdf_agent = PDFAgent()