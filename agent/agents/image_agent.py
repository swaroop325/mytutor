"""
Image Agent - Specialized processor for image files with advanced vision capabilities
Handles: JPG, JPEG, PNG, GIF, WebP, BMP, TIFF, SVG files
Features: OCR, chart/diagram interpretation, handwriting recognition, educational content analysis
"""
import os
import json
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
import boto3
from strands import Agent
import base64
import io
import logging
from dataclasses import dataclass

try:
    from ..config.model_manager import model_config_manager
except ImportError:
    # Fallback for when not running as package
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from config.model_manager import model_config_manager


logger = logging.getLogger(__name__)


@dataclass
class EducationalDiagram:
    """Detected educational diagram or flowchart."""
    diagram_type: str  # flowchart, mind_map, organizational_chart, concept_map, etc.
    complexity: str    # simple, moderate, complex
    subject_area: str  # math, science, business, etc.
    elements: List[str]  # detected elements like nodes, connections, labels
    confidence: float
    educational_level: str  # elementary, middle_school, high_school, college


@dataclass
class VisualCategory:
    """Visual element category with confidence."""
    category: str      # graph, illustration, screenshot, photo, etc.
    subcategory: str   # bar_chart, line_graph, pie_chart, etc.
    confidence: float
    features: Dict[str, Any]  # specific features detected


@dataclass
class OCRResult:
    """Result from OCR processing."""
    text: str
    confidence: float
    bounding_boxes: List[Dict[str, Any]]
    detected_languages: List[str]


@dataclass
class VisualElement:
    """Detected visual element in image."""
    element_type: str  # chart, diagram, table, handwriting, etc.
    confidence: float
    description: str
    bounding_box: Optional[Dict[str, float]] = None
    extracted_data: Optional[Dict[str, Any]] = None


@dataclass
class ImageAnalysisResult:
    """Comprehensive image analysis result."""
    content_type: str
    educational_value: float
    visual_elements: List[VisualElement]
    ocr_result: Optional[OCRResult]
    key_concepts: List[str]
    difficulty_level: str
    confidence_score: float


class ImageAgent:
    """Enhanced image agent with advanced vision capabilities."""
    
    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self.agent = Agent()
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=region)
        self.textract_client = boto3.client('textract', region_name=region)
        self.supported_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.svg']
        self.model_config = model_config_manager.get_model_for_agent("image", "image")
    
    def can_process(self, file_path: str) -> bool:
        """Check if this agent can process the given file."""
        return any(file_path.lower().endswith(ext) for ext in self.supported_extensions)
    
    def _resolve_file_path(self, file_path: str) -> str:
        """Resolve file path relative to project structure."""
        from pathlib import Path
        
        file_path_obj = Path(file_path)
        print(f"🔍 IMAGE Agent - Resolving file path: {file_path_obj}")
        
        # If the path exists as-is, use it
        if file_path_obj.exists():
            print(f"✅ IMAGE Agent - Found file at original path: {file_path_obj}")
            return str(file_path_obj)
        
        # Try in backend directory (most common case)
        backend_path = Path("backend") / file_path_obj
        if backend_path.exists():
            print(f"✅ IMAGE Agent - Found file at backend path: {backend_path}")
            return str(backend_path)
        
        # Try relative to backend directory (from agent directory)
        backend_relative_path = Path("../backend") / file_path_obj
        if backend_relative_path.exists():
            print(f"✅ IMAGE Agent - Found file at backend relative path: {backend_relative_path}")
            return str(backend_relative_path)
        
        # Return original path if nothing works
        print(f"❌ IMAGE Agent - Could not resolve file path, using original: {file_path_obj}")
        return file_path
    
    async def process_file(self, file_path: str, user_id: str) -> Dict[str, Any]:
        """Process an image file with enhanced vision capabilities."""
        try:
            print(f"🖼️ Enhanced IMAGE Agent processing: {file_path}")

            # Resolve file path
            resolved_path = self._resolve_file_path(file_path)

            # Extract basic image content and metadata
            image_data = await self._extract_image_content(resolved_path)

            # Perform OCR extraction
            ocr_result = await self._extract_text_with_ocr(resolved_path)
            
            # Analyze visual content with AI vision
            visual_analysis = await self._analyze_visual_content(image_data, file_path)
            
            # Detect and analyze educational elements
            educational_analysis = await self._analyze_educational_content(
                image_data, ocr_result, visual_analysis, file_path
            )
            
            # Prepare comprehensive result
            result = {
                "agent_type": "image",
                "file_path": file_path,
                "status": "completed",
                "content": {
                    # Basic image properties
                    "dimensions": image_data['metadata']['dimensions'],
                    "format": image_data['metadata']['format'],
                    "mode": image_data['metadata']['mode'],
                    "has_transparency": image_data['metadata']['has_transparency'],
                    "dominant_colors": image_data.get('dominant_colors', []),
                    "thumbnail_base64": image_data.get('thumbnail_base64', ''),
                    
                    # Enhanced content extraction
                    "extracted_text": ocr_result.text if ocr_result else "",
                    "text_confidence": ocr_result.confidence if ocr_result else 0.0,
                    "detected_languages": ocr_result.detected_languages if ocr_result else [],
                    "visual_elements": [
                        {
                            "type": elem.element_type,
                            "confidence": elem.confidence,
                            "description": elem.description,
                            "bounding_box": elem.bounding_box,
                            "extracted_data": elem.extracted_data
                        }
                        for elem in visual_analysis.visual_elements
                    ] if visual_analysis else [],
                    
                    # Educational analysis
                    "educational_value": educational_analysis.educational_value if educational_analysis else 0.0,
                    "key_concepts": educational_analysis.key_concepts if educational_analysis else [],
                    "difficulty_level": educational_analysis.difficulty_level if educational_analysis else "unknown",
                    "content_type": educational_analysis.content_type if educational_analysis else "general_image"
                },
                "analysis": {
                    "ai_analysis": visual_analysis.content_type if visual_analysis else "Basic image processing",
                    "confidence_score": educational_analysis.confidence_score if educational_analysis else 0.5,
                    "processing_method": "enhanced_vision_analysis_with_ocr",
                    "model_used": self.model_config.model_id if self.model_config else "default"
                },
                "metadata": {
                    **image_data['metadata'],
                    "processed_by": "enhanced_image_agent",
                    "has_text": bool(ocr_result and ocr_result.text.strip()),
                    "has_educational_content": bool(educational_analysis and educational_analysis.educational_value > 0.3)
                }
            }
            
            print(f"✅ Enhanced IMAGE Agent completed: {file_path} "
                  f"({image_data['metadata']['dimensions']}, "
                  f"Educational Value: {educational_analysis.educational_value if educational_analysis else 0:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"Enhanced IMAGE Agent error processing {file_path}: {e}")
            # Fallback to basic processing
            try:
                return await self._fallback_basic_processing(file_path)
            except Exception as fallback_error:
                logger.error(f"Fallback processing also failed: {fallback_error}")
                return {
                    "agent_type": "image",
                    "file_path": file_path,
                    "status": "error",
                    "error": str(e)
                }
    
    async def _extract_image_content(self, file_path: str) -> Dict[str, Any]:
        """Extract image content and metadata."""
        try:
            # Handle SVG files separately
            if file_path.lower().endswith('.svg'):
                return await self._process_svg(file_path)
            
            # Resolve file path first
            resolved_path = self._resolve_file_path(file_path)
            print(f"🖼️ IMAGE Agent processing resolved path: {resolved_path}")
            
            # Open and process regular image files
            with Image.open(resolved_path) as img:
                # Get basic metadata
                metadata = {
                    "dimensions": f"{img.width}x{img.height}",
                    "width": img.width,
                    "height": img.height,
                    "format": img.format,
                    "mode": img.mode,
                    "has_transparency": img.mode in ('RGBA', 'LA') or 'transparency' in img.info,
                    "file_size": os.path.getsize(file_path),
                    "file_type": Path(file_path).suffix.lower()
                }
                
                # Add EXIF data if available
                if hasattr(img, '_getexif') and img._getexif():
                    exif_data = img._getexif()
                    if exif_data:
                        metadata['has_exif'] = True
                        # Add some common EXIF fields
                        metadata['exif'] = {
                            'make': exif_data.get(271, ''),
                            'model': exif_data.get(272, ''),
                            'datetime': exif_data.get(306, ''),
                            'orientation': exif_data.get(274, 1)
                        }
                else:
                    metadata['has_exif'] = False
                
                # Create thumbnail for analysis
                thumbnail = img.copy()
                thumbnail.thumbnail((512, 512), Image.Resampling.LANCZOS)
                
                # Convert to RGB if necessary for JPEG encoding
                if thumbnail.mode in ('RGBA', 'LA', 'P'):
                    thumbnail = thumbnail.convert('RGB')
                
                # Convert to base64
                buffer = io.BytesIO()
                thumbnail.save(buffer, format='JPEG', quality=85)
                thumbnail_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                # Extract dominant colors (simplified)
                dominant_colors = await self._extract_dominant_colors(img)
                
                return {
                    "metadata": metadata,
                    "thumbnail_base64": thumbnail_base64,
                    "dominant_colors": dominant_colors
                }
                
        except Exception as e:
            print(f"⚠️ Error processing image {file_path}: {e}")
            return {
                "metadata": {
                    "dimensions": "unknown",
                    "format": "unknown",
                    "file_size": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                    "file_type": Path(file_path).suffix.lower(),
                    "error": str(e)
                },
                "thumbnail_base64": "",
                "dominant_colors": []
            }
    
    async def _process_svg(self, file_path: str) -> Dict[str, Any]:
        """Process SVG files."""
        try:
            # Resolve file path first
            resolved_path = self._resolve_file_path(file_path)
            
            with open(resolved_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()
            
            metadata = {
                "dimensions": "vector",
                "format": "SVG",
                "mode": "vector",
                "has_transparency": True,
                "file_size": os.path.getsize(file_path),
                "file_type": ".svg",
                "content_length": len(svg_content)
            }
            
            return {
                "metadata": metadata,
                "thumbnail_base64": "",  # SVG thumbnails would need special handling
                "dominant_colors": [],
                "svg_content": svg_content[:1000]  # First 1000 chars for analysis
            }
            
        except Exception as e:
            return {
                "metadata": {
                    "dimensions": "unknown",
                    "format": "SVG",
                    "file_size": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                    "file_type": ".svg",
                    "error": str(e)
                },
                "thumbnail_base64": "",
                "dominant_colors": []
            }
    
    async def _extract_dominant_colors(self, img: Image.Image) -> List[str]:
        """Extract dominant colors from image."""
        try:
            # Convert to RGB and resize for faster processing
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            img_small = img.resize((50, 50))
            
            # Get colors and their counts
            colors = img_small.getcolors(maxcolors=256)
            if not colors:
                return []
            
            # Sort by frequency and get top 5
            colors.sort(key=lambda x: x[0], reverse=True)
            dominant_colors = []
            
            for count, color in colors[:5]:
                hex_color = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
                dominant_colors.append(hex_color)
            
            return dominant_colors
            
        except Exception as e:
            print(f"⚠️ Error extracting colors: {e}")
            return []
    
    async def _extract_text_with_ocr(self, file_path: str) -> Optional[OCRResult]:
        """Extract text from image using AWS Textract with enhanced capabilities."""
        try:
            # Skip OCR for SVG files
            if file_path.lower().endswith('.svg'):
                return None
            
            # Resolve file path and read image file
            resolved_path = self._resolve_file_path(file_path)
            
            with open(resolved_path, 'rb') as image_file:
                image_bytes = image_file.read()
            
            # Use AWS Textract for OCR
            try:
                response = self.textract_client.detect_document_text(
                    Document={'Bytes': image_bytes}
                )
                
                # Extract text and confidence scores
                extracted_text = []
                bounding_boxes = []
                confidences = []
                
                for block in response.get('Blocks', []):
                    if block['BlockType'] == 'LINE':
                        text = block.get('Text', '')
                        confidence = block.get('Confidence', 0.0)
                        
                        if text.strip():
                            extracted_text.append(text)
                            confidences.append(confidence)
                            
                            # Extract bounding box
                            if 'Geometry' in block:
                                bbox = block['Geometry']['BoundingBox']
                                bounding_boxes.append({
                                    'text': text,
                                    'left': bbox['Left'],
                                    'top': bbox['Top'],
                                    'width': bbox['Width'],
                                    'height': bbox['Height'],
                                    'confidence': confidence
                                })
                
                if extracted_text:
                    full_text = '\n'.join(extracted_text)
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
                    
                    # Detect languages (simplified - could be enhanced with language detection)
                    detected_languages = self._detect_languages(full_text)
                    
                    return OCRResult(
                        text=full_text,
                        confidence=avg_confidence / 100.0,  # Convert to 0-1 scale
                        bounding_boxes=bounding_boxes,
                        detected_languages=detected_languages
                    )
                
            except Exception as textract_error:
                logger.warning(f"AWS Textract failed, trying fallback OCR: {textract_error}")
                # Fallback to basic PIL-based text detection (limited capability)
                return await self._fallback_ocr(file_path)
            
            return None
            
        except Exception as e:
            logger.error(f"Error in OCR extraction: {e}")
            return None
    
    async def _fallback_ocr(self, file_path: str) -> Optional[OCRResult]:
        """Fallback OCR using basic image processing techniques."""
        try:
            # Resolve file path first
            resolved_path = self._resolve_file_path(file_path)
            
            # This is a simplified fallback - in production, you might use pytesseract
            # For now, we'll use the AI model to detect text
            with Image.open(resolved_path) as img:
                # Enhance image for better text detection
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Apply image enhancements
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(2.0)
                
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(2.0)
                
                # Convert to base64 for AI analysis
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=95)
                img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                # Use AI model to detect text
                text_content = await self._ai_text_detection(img_base64)
                
                if text_content:
                    return OCRResult(
                        text=text_content,
                        confidence=0.7,  # Lower confidence for fallback method
                        bounding_boxes=[],
                        detected_languages=['en']  # Default assumption
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Fallback OCR failed: {e}")
            return None
    
    def _detect_languages(self, text: str) -> List[str]:
        """Detect languages in extracted text (simplified implementation)."""
        # This is a basic implementation - could be enhanced with proper language detection
        if not text.strip():
            return []
        
        # Simple heuristics for common languages
        languages = ['en']  # Default to English
        
        # Check for common non-English characters
        if any(ord(char) > 127 for char in text):
            # Contains non-ASCII characters, might be other languages
            if any(char in 'àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ' for char in text.lower()):
                languages.append('es')  # Spanish/French indicators
            if any(char in 'äöüß' for char in text.lower()):
                languages.append('de')  # German indicators
        
        return languages
    
    async def _ai_text_detection(self, image_base64: str) -> Optional[str]:
        """Use AI model to detect and extract text from image."""
        try:
            if not self.model_config:
                return None
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_config.model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Extract all visible text from this image. Return only the text content, preserving line breaks and formatting where possible. If no text is visible, return 'NO_TEXT_DETECTED'."
                                },
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/jpeg",
                                        "data": image_base64
                                    }
                                }
                            ]
                        }
                    ]
                })
            )
            
            result = json.loads(response['body'].read())
            text_content = result['content'][0]['text'].strip()
            
            if text_content and text_content != 'NO_TEXT_DETECTED':
                return text_content
            
            return None
            
        except Exception as e:
            logger.error(f"AI text detection failed: {e}")
            return None
    
    async def _analyze_visual_content(self, image_data: Dict[str, Any], file_path: str) -> Optional[ImageAnalysisResult]:
        """Analyze visual content to detect charts, diagrams, and educational elements."""
        try:
            if not self.model_config:
                return None
            
            metadata = image_data['metadata']
            thumbnail_base64 = image_data.get('thumbnail_base64', '')
            
            if not thumbnail_base64:
                return None
            
            # Perform enhanced analysis with new methods
            diagrams = await self.detect_educational_diagrams(thumbnail_base64)
            categories = await self.categorize_visual_elements(thumbnail_base64)
            
            # Continue with existing detailed analysis
            
            # Prepare detailed analysis prompt
            analysis_prompt = f"""
Analyze this image for educational and visual content. Provide a detailed analysis in JSON format:

Image Details:
- File: {Path(file_path).name}
- Dimensions: {metadata.get('dimensions', 'Unknown')}
- Format: {metadata.get('format', 'Unknown')}

Please analyze and identify:

1. **Visual Element Types**: Detect and categorize visual elements:
   - Charts (bar, line, pie, scatter, histogram, etc.)
   - Diagrams (flowcharts, organizational charts, mind maps, etc.)
   - Tables and data grids
   - Mathematical equations or formulas
   - Handwritten notes or annotations
   - Screenshots of software/applications
   - Photographs vs. illustrations
   - Technical drawings or schematics

2. **Educational Content Analysis**:
   - Subject area (math, science, history, language, etc.)
   - Educational level (elementary, middle school, high school, college, professional)
   - Key concepts and topics visible
   - Learning objectives that could be addressed
   - Difficulty assessment

3. **Content Structure**:
   - Text layout and hierarchy
   - Visual organization and flow
   - Relationships between elements
   - Data presentation quality

4. **Technical Quality**:
   - Image clarity and readability
   - Color usage and accessibility
   - Professional vs. informal presentation

Return your analysis as a JSON object with this structure:
{{
    "visual_elements": [
        {{
            "type": "chart|diagram|table|equation|handwriting|screenshot|photo|illustration|technical_drawing",
            "subtype": "specific type (e.g., bar_chart, flowchart, data_table)",
            "confidence": 0.0-1.0,
            "description": "detailed description",
            "educational_value": 0.0-1.0,
            "complexity": "low|medium|high"
        }}
    ],
    "educational_analysis": {{
        "subject_areas": ["list of subjects"],
        "education_level": "elementary|middle_school|high_school|college|professional",
        "key_concepts": ["list of key concepts"],
        "difficulty_level": "beginner|intermediate|advanced",
        "learning_objectives": ["potential learning objectives"]
    }},
    "content_quality": {{
        "clarity": 0.0-1.0,
        "organization": 0.0-1.0,
        "accessibility": 0.0-1.0,
        "professional_quality": 0.0-1.0
    }},
    "overall_assessment": {{
        "content_type": "educational|reference|illustration|data_visualization|mixed",
        "educational_value": 0.0-1.0,
        "confidence_score": 0.0-1.0
    }}
}}
"""
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_config.model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2000,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": analysis_prompt
                                },
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/jpeg",
                                        "data": thumbnail_base64
                                    }
                                }
                            ]
                        }
                    ]
                })
            )
            
            result = json.loads(response['body'].read())
            analysis_text = result['content'][0]['text']
            
            # Parse JSON response
            try:
                analysis_data = json.loads(analysis_text)
                return self._parse_visual_analysis(analysis_data, diagrams, categories)
            except json.JSONDecodeError:
                # Fallback: extract information from text response
                return self._parse_text_analysis(analysis_text, diagrams, categories)
            
        except Exception as e:
            logger.error(f"Error in visual content analysis: {e}")
            return None
    
    def _parse_visual_analysis(self, analysis_data: Dict[str, Any], 
                             diagrams: List[EducationalDiagram],
                             categories: List[VisualCategory]) -> ImageAnalysisResult:
        """Parse structured visual analysis data with enhanced diagram and category info."""
        visual_elements = []
        
        # Add elements from original analysis
        for elem_data in analysis_data.get('visual_elements', []):
            element = VisualElement(
                element_type=elem_data.get('type', 'unknown'),
                confidence=elem_data.get('confidence', 0.5),
                description=elem_data.get('description', ''),
                extracted_data={
                    'subtype': elem_data.get('subtype', ''),
                    'educational_value': elem_data.get('educational_value', 0.0),
                    'complexity': elem_data.get('complexity', 'medium')
                }
            )
            visual_elements.append(element)
        
        # Add elements from diagram detection
        for diagram in diagrams:
            element = VisualElement(
                element_type='educational_diagram',
                confidence=diagram.confidence,
                description=f"{diagram.diagram_type} - {diagram.subject_area} ({diagram.complexity})",
                extracted_data={
                    'diagram_type': diagram.diagram_type,
                    'subject_area': diagram.subject_area,
                    'complexity': diagram.complexity,
                    'educational_level': diagram.educational_level,
                    'elements': diagram.elements
                }
            )
            visual_elements.append(element)
        
        # Add elements from categorization
        for category in categories:
            element = VisualElement(
                element_type='visual_category',
                confidence=category.confidence,
                description=f"{category.category} - {category.subcategory}",
                extracted_data={
                    'category': category.category,
                    'subcategory': category.subcategory,
                    'features': category.features
                }
            )
            visual_elements.append(element)
        
        educational_analysis = analysis_data.get('educational_analysis', {})
        overall_assessment = analysis_data.get('overall_assessment', {})
        
        # Enhanced educational value calculation
        base_educational_value = overall_assessment.get('educational_value', 0.0)
        diagram_boost = len(diagrams) * 0.2  # Boost for educational diagrams
        educational_value = min(base_educational_value + diagram_boost, 1.0)
        
        return ImageAnalysisResult(
            content_type=overall_assessment.get('content_type', 'general_image'),
            educational_value=educational_value,
            visual_elements=visual_elements,
            ocr_result=None,  # Will be set separately
            key_concepts=educational_analysis.get('key_concepts', []),
            difficulty_level=educational_analysis.get('difficulty_level', 'unknown'),
            confidence_score=overall_assessment.get('confidence_score', 0.5)
        )
    
    def _parse_text_analysis(self, analysis_text: str,
                           diagrams: List[EducationalDiagram],
                           categories: List[VisualCategory]) -> ImageAnalysisResult:
        """Parse unstructured text analysis as fallback with enhanced data."""
        visual_elements = []
        
        # Look for common visual element indicators
        element_types = ['chart', 'diagram', 'table', 'equation', 'graph', 'flowchart']
        for elem_type in element_types:
            if elem_type.lower() in analysis_text.lower():
                element = VisualElement(
                    element_type=elem_type,
                    confidence=0.6,
                    description=f"Detected {elem_type} in image",
                    extracted_data={'complexity': 'medium'}
                )
                visual_elements.append(element)
        
        # Add diagram elements
        for diagram in diagrams:
            element = VisualElement(
                element_type='educational_diagram',
                confidence=diagram.confidence,
                description=f"{diagram.diagram_type} - {diagram.subject_area}",
                extracted_data={
                    'diagram_type': diagram.diagram_type,
                    'subject_area': diagram.subject_area,
                    'complexity': diagram.complexity
                }
            )
            visual_elements.append(element)
        
        # Add category elements
        for category in categories:
            element = VisualElement(
                element_type='visual_category',
                confidence=category.confidence,
                description=f"{category.category} - {category.subcategory}",
                extracted_data={
                    'category': category.category,
                    'subcategory': category.subcategory
                }
            )
            visual_elements.append(element)
        
        # Estimate educational value based on content and diagrams
        educational_indicators = ['educational', 'learning', 'academic', 'study', 'course', 'lesson']
        educational_value = 0.3  # Default
        for indicator in educational_indicators:
            if indicator in analysis_text.lower():
                educational_value = 0.7
                break
        
        # Boost educational value for detected diagrams
        if diagrams:
            educational_value = min(educational_value + len(diagrams) * 0.15, 1.0)
        
        return ImageAnalysisResult(
            content_type='general_image',
            educational_value=educational_value,
            visual_elements=visual_elements,
            ocr_result=None,
            key_concepts=[],
            difficulty_level='unknown',
            confidence_score=0.5
        )
    
    async def _analyze_educational_content(self, image_data: Dict[str, Any], 
                                         ocr_result: Optional[OCRResult],
                                         visual_analysis: Optional[ImageAnalysisResult],
                                         file_path: str) -> Optional[ImageAnalysisResult]:
        """Combine OCR and visual analysis for comprehensive educational assessment."""
        try:
            if not visual_analysis:
                visual_analysis = ImageAnalysisResult(
                    content_type='general_image',
                    educational_value=0.0,
                    visual_elements=[],
                    ocr_result=ocr_result,
                    key_concepts=[],
                    difficulty_level='unknown',
                    confidence_score=0.3
                )
            
            # Add OCR result to analysis
            visual_analysis.ocr_result = ocr_result
            
            # Extract diagrams and categories from visual elements for confidence calculation
            diagrams = []
            categories = []
            
            for element in visual_analysis.visual_elements:
                if element.element_type == 'educational_diagram' and element.extracted_data:
                    diagram = EducationalDiagram(
                        diagram_type=element.extracted_data.get('diagram_type', 'unknown'),
                        complexity=element.extracted_data.get('complexity', 'medium'),
                        subject_area=element.extracted_data.get('subject_area', 'general'),
                        elements=element.extracted_data.get('elements', []),
                        confidence=element.confidence,
                        educational_level=element.extracted_data.get('educational_level', 'unknown')
                    )
                    diagrams.append(diagram)
                elif element.element_type == 'visual_category' and element.extracted_data:
                    category = VisualCategory(
                        category=element.extracted_data.get('category', 'unknown'),
                        subcategory=element.extracted_data.get('subcategory', ''),
                        confidence=element.confidence,
                        features=element.extracted_data.get('features', {})
                    )
                    categories.append(category)
            
            # Calculate enhanced confidence score
            enhanced_confidence = await self.calculate_confidence_scores(
                visual_analysis, ocr_result, diagrams, categories
            )
            visual_analysis.confidence_score = enhanced_confidence
            
            # Enhance analysis with text content if available
            if ocr_result and ocr_result.text.strip():
                enhanced_analysis = await self._enhance_with_text_analysis(
                    visual_analysis, ocr_result.text
                )
                if enhanced_analysis:
                    return enhanced_analysis
            
            return visual_analysis
            
        except Exception as e:
            logger.error(f"Error in educational content analysis: {e}")
            return visual_analysis
    
    async def _enhance_with_text_analysis(self, visual_analysis: ImageAnalysisResult, 
                                        extracted_text: str) -> Optional[ImageAnalysisResult]:
        """Enhance visual analysis with extracted text content."""
        try:
            if not self.model_config:
                return visual_analysis
            
            enhancement_prompt = f"""
Based on the extracted text and visual analysis, provide enhanced educational assessment:

Extracted Text:
{extracted_text[:1000]}  # Limit text length

Visual Elements Detected: {len(visual_analysis.visual_elements)}
Current Educational Value: {visual_analysis.educational_value}

Please provide enhanced analysis in JSON format:
{{
    "enhanced_key_concepts": ["list of key concepts from text and visuals"],
    "subject_classification": "primary subject area",
    "difficulty_assessment": "beginner|intermediate|advanced",
    "educational_value": 0.0-1.0,
    "learning_objectives": ["specific learning objectives"],
    "content_summary": "brief summary of educational content"
}}
"""
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_config.model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 800,
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": enhancement_prompt}]
                        }
                    ]
                })
            )
            
            result = json.loads(response['body'].read())
            enhancement_text = result['content'][0]['text']
            
            try:
                enhancement_data = json.loads(enhancement_text)
                
                # Update visual analysis with enhanced data
                visual_analysis.key_concepts = enhancement_data.get('enhanced_key_concepts', visual_analysis.key_concepts)
                visual_analysis.difficulty_level = enhancement_data.get('difficulty_assessment', visual_analysis.difficulty_level)
                visual_analysis.educational_value = max(
                    visual_analysis.educational_value,
                    enhancement_data.get('educational_value', 0.0)
                )
                visual_analysis.confidence_score = min(visual_analysis.confidence_score + 0.2, 1.0)
                
                return visual_analysis
                
            except json.JSONDecodeError:
                logger.warning("Could not parse enhancement JSON, using original analysis")
                return visual_analysis
            
        except Exception as e:
            logger.error(f"Error enhancing with text analysis: {e}")
            return visual_analysis
    
    async def _fallback_basic_processing(self, file_path: str) -> Dict[str, Any]:
        """Fallback to basic image processing when enhanced processing fails."""
        try:
            image_data = await self._extract_image_content(file_path)
            
            return {
                "agent_type": "image",
                "file_path": file_path,
                "status": "completed_basic",
                "content": {
                    "dimensions": image_data['metadata']['dimensions'],
                    "format": image_data['metadata']['format'],
                    "mode": image_data['metadata']['mode'],
                    "has_transparency": image_data['metadata']['has_transparency'],
                    "dominant_colors": image_data.get('dominant_colors', []),
                    "thumbnail_base64": image_data.get('thumbnail_base64', ''),
                    "extracted_text": "",
                    "text_confidence": 0.0,
                    "visual_elements": [],
                    "educational_value": 0.0,
                    "key_concepts": [],
                    "difficulty_level": "unknown",
                    "content_type": "general_image"
                },
                "analysis": {
                    "ai_analysis": "Basic processing only - enhanced features unavailable",
                    "confidence_score": 0.3,
                    "processing_method": "basic_fallback",
                    "model_used": "none"
                },
                "metadata": {
                    **image_data['metadata'],
                    "processed_by": "basic_image_agent",
                    "has_text": False,
                    "has_educational_content": False
                }
            }
            
        except Exception as e:
            logger.error(f"Even basic processing failed: {e}")
            raise
    
    async def _analyze_content(self, image_data: Dict[str, Any], file_path: str) -> Dict[str, Any]:
        """Legacy analyze content method for backward compatibility."""
        try:
            # Use the new enhanced analysis but return in legacy format
            visual_analysis = await self._analyze_visual_content(image_data, file_path)
            
            if visual_analysis:
                # Convert to legacy format
                analysis_summary = f"Enhanced analysis detected {len(visual_analysis.visual_elements)} visual elements. "
                analysis_summary += f"Educational value: {visual_analysis.educational_value:.2f}. "
                analysis_summary += f"Content type: {visual_analysis.content_type}. "
                
                if visual_analysis.key_concepts:
                    analysis_summary += f"Key concepts: {', '.join(visual_analysis.key_concepts[:3])}."
                
                return {
                    "ai_analysis": analysis_summary,
                    "content_type": "image_file",
                    "processing_method": "enhanced_vision_analysis",
                    "dimensions": image_data['metadata'].get('dimensions', 'unknown'),
                    "dominant_colors": image_data.get('dominant_colors', []),
                    "educational_value": visual_analysis.educational_value,
                    "confidence_score": visual_analysis.confidence_score
                }
            else:
                # Fallback to basic analysis
                return await self._basic_legacy_analysis(image_data, file_path)
            
        except Exception as e:
            logger.error(f"Error in legacy analysis: {e}")
            return await self._basic_legacy_analysis(image_data, file_path)
    
    async def _basic_legacy_analysis(self, image_data: Dict[str, Any], file_path: str) -> Dict[str, Any]:
        """Basic legacy analysis as fallback."""
        metadata = image_data['metadata']
        
        return {
            "ai_analysis": f"Basic image analysis: {metadata.get('format', 'Unknown')} format, "
                          f"{metadata.get('dimensions', 'unknown')} dimensions",
            "content_type": "image_file",
            "processing_method": "basic_metadata_only",
            "dimensions": metadata.get('dimensions', 'unknown'),
            "dominant_colors": image_data.get('dominant_colors', []),
            "educational_value": 0.0,
            "confidence_score": 0.3
        }
    
    async def detect_educational_diagrams(self, image_base64: str) -> List[EducationalDiagram]:
        """Detect and analyze educational diagrams and flowcharts."""
        try:
            if not self.model_config:
                return []
            
            diagram_prompt = """
Analyze this image specifically for educational diagrams and flowcharts. Identify and categorize any structured visual learning aids.

Look for these types of educational diagrams:
1. **Flowcharts**: Process flows, decision trees, algorithm diagrams
2. **Mind Maps**: Central topic with branching subtopics
3. **Organizational Charts**: Hierarchical structures, family trees
4. **Concept Maps**: Relationships between concepts with connecting lines/labels
5. **Venn Diagrams**: Overlapping circles showing relationships
6. **Timeline Diagrams**: Sequential events or processes
7. **Network Diagrams**: Interconnected nodes and relationships
8. **System Diagrams**: Input-process-output models, system architecture
9. **Scientific Diagrams**: Biological processes, chemical reactions, physics concepts
10. **Mathematical Diagrams**: Geometric shapes, graphs, mathematical proofs

For each diagram detected, provide:
- Type and subtype
- Complexity level (simple/moderate/complex)
- Subject area (math, science, business, history, etc.)
- Key elements visible (nodes, connections, labels, symbols)
- Educational level (elementary through college)
- Confidence score (0.0-1.0)

Return as JSON array:
[
    {
        "diagram_type": "flowchart|mind_map|organizational_chart|concept_map|venn_diagram|timeline|network|system|scientific|mathematical",
        "subtype": "specific subtype",
        "complexity": "simple|moderate|complex",
        "subject_area": "subject",
        "elements": ["list of detected elements"],
        "educational_level": "elementary|middle_school|high_school|college|professional",
        "confidence": 0.0-1.0,
        "description": "detailed description"
    }
]

If no educational diagrams are detected, return an empty array [].
"""
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_config.model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1500,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": diagram_prompt
                                },
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/jpeg",
                                        "data": image_base64
                                    }
                                }
                            ]
                        }
                    ]
                })
            )
            
            result = json.loads(response['body'].read())
            analysis_text = result['content'][0]['text'].strip()
            
            try:
                # Try to parse as JSON
                diagrams_data = json.loads(analysis_text)
                if not isinstance(diagrams_data, list):
                    return []
                
                diagrams = []
                for diagram_data in diagrams_data:
                    diagram = EducationalDiagram(
                        diagram_type=diagram_data.get('diagram_type', 'unknown'),
                        complexity=diagram_data.get('complexity', 'moderate'),
                        subject_area=diagram_data.get('subject_area', 'general'),
                        elements=diagram_data.get('elements', []),
                        confidence=diagram_data.get('confidence', 0.5),
                        educational_level=diagram_data.get('educational_level', 'unknown')
                    )
                    diagrams.append(diagram)
                
                return diagrams
                
            except json.JSONDecodeError:
                # Fallback: parse text response for diagram indicators
                return self._parse_diagram_text(analysis_text)
            
        except Exception as e:
            logger.error(f"Error detecting educational diagrams: {e}")
            return []
    
    def _parse_diagram_text(self, analysis_text: str) -> List[EducationalDiagram]:
        """Parse text response for diagram indicators as fallback."""
        diagrams = []
        text_lower = analysis_text.lower()
        
        # Common diagram type indicators
        diagram_indicators = {
            'flowchart': ['flowchart', 'flow chart', 'process flow', 'workflow'],
            'mind_map': ['mind map', 'mindmap', 'concept map', 'brain map'],
            'organizational_chart': ['org chart', 'organizational', 'hierarchy', 'family tree'],
            'venn_diagram': ['venn', 'overlapping circles', 'set diagram'],
            'timeline': ['timeline', 'chronology', 'sequence', 'historical'],
            'scientific': ['scientific', 'biology', 'chemistry', 'physics', 'anatomy'],
            'mathematical': ['mathematical', 'geometry', 'graph', 'equation', 'formula']
        }
        
        for diagram_type, indicators in diagram_indicators.items():
            for indicator in indicators:
                if indicator in text_lower:
                    diagram = EducationalDiagram(
                        diagram_type=diagram_type,
                        complexity='moderate',
                        subject_area=self._infer_subject_area(text_lower),
                        elements=[],
                        confidence=0.6,
                        educational_level='high_school'
                    )
                    diagrams.append(diagram)
                    break  # Only add one per type
        
        return diagrams
    
    def _infer_subject_area(self, text: str) -> str:
        """Infer subject area from text content."""
        subject_keywords = {
            'math': ['math', 'algebra', 'geometry', 'calculus', 'equation', 'formula'],
            'science': ['science', 'biology', 'chemistry', 'physics', 'experiment'],
            'business': ['business', 'management', 'organization', 'company', 'corporate'],
            'history': ['history', 'historical', 'timeline', 'chronology', 'events'],
            'computer_science': ['algorithm', 'programming', 'software', 'computer', 'code']
        }
        
        for subject, keywords in subject_keywords.items():
            if any(keyword in text for keyword in keywords):
                return subject
        
        return 'general'
    
    async def categorize_visual_elements(self, image_base64: str) -> List[VisualCategory]:
        """Categorize visual elements with confidence scoring."""
        try:
            if not self.model_config:
                return []
            
            categorization_prompt = """
Analyze this image and categorize all visual elements. Provide detailed categorization with confidence scores.

**Primary Categories to identify:**
1. **Graphs & Charts**: bar_chart, line_graph, pie_chart, scatter_plot, histogram, area_chart
2. **Illustrations**: technical_illustration, artistic_drawing, infographic, icon_set, logo
3. **Screenshots**: software_interface, web_page, mobile_app, desktop_application
4. **Photographs**: portrait, landscape, object_photo, group_photo, documentary
5. **Technical Drawings**: blueprint, schematic, engineering_drawing, architectural_plan
6. **Educational Materials**: textbook_page, worksheet, presentation_slide, poster
7. **Data Visualizations**: dashboard, report, table, matrix, heatmap
8. **Handwritten Content**: notes, annotations, sketches, handwritten_text

**For each element, analyze:**
- Visual style (professional, informal, academic, artistic)
- Color usage and accessibility
- Text density and readability
- Interactive elements (if any)
- Educational appropriateness
- Technical quality

Return as JSON array:
[
    {
        "category": "primary category",
        "subcategory": "specific type",
        "confidence": 0.0-1.0,
        "features": {
            "style": "professional|informal|academic|artistic",
            "color_accessibility": 0.0-1.0,
            "text_readability": 0.0-1.0,
            "educational_value": 0.0-1.0,
            "technical_quality": 0.0-1.0,
            "complexity": "low|medium|high"
        },
        "description": "detailed description"
    }
]
"""
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_config.model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1200,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": categorization_prompt
                                },
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/jpeg",
                                        "data": image_base64
                                    }
                                }
                            ]
                        }
                    ]
                })
            )
            
            result = json.loads(response['body'].read())
            analysis_text = result['content'][0]['text'].strip()
            
            try:
                categories_data = json.loads(analysis_text)
                if not isinstance(categories_data, list):
                    return []
                
                categories = []
                for cat_data in categories_data:
                    category = VisualCategory(
                        category=cat_data.get('category', 'unknown'),
                        subcategory=cat_data.get('subcategory', ''),
                        confidence=cat_data.get('confidence', 0.5),
                        features=cat_data.get('features', {})
                    )
                    categories.append(category)
                
                return categories
                
            except json.JSONDecodeError:
                # Fallback categorization
                return self._fallback_categorization(analysis_text)
            
        except Exception as e:
            logger.error(f"Error categorizing visual elements: {e}")
            return []
    
    def _fallback_categorization(self, analysis_text: str) -> List[VisualCategory]:
        """Fallback visual categorization based on text analysis."""
        categories = []
        text_lower = analysis_text.lower()
        
        # Basic category detection
        category_indicators = {
            'chart': ['chart', 'graph', 'bar', 'pie', 'line graph'],
            'illustration': ['illustration', 'drawing', 'artwork', 'graphic'],
            'screenshot': ['screenshot', 'interface', 'software', 'application'],
            'photograph': ['photo', 'picture', 'image', 'portrait'],
            'educational': ['educational', 'textbook', 'worksheet', 'slide']
        }
        
        for category, indicators in category_indicators.items():
            for indicator in indicators:
                if indicator in text_lower:
                    visual_cat = VisualCategory(
                        category=category,
                        subcategory='general',
                        confidence=0.6,
                        features={
                            'style': 'unknown',
                            'educational_value': 0.5,
                            'technical_quality': 0.5,
                            'complexity': 'medium'
                        }
                    )
                    categories.append(visual_cat)
                    break
        
        # If no categories detected, add a general one
        if not categories:
            categories.append(VisualCategory(
                category='general_image',
                subcategory='unspecified',
                confidence=0.4,
                features={'complexity': 'medium'}
            ))
        
        return categories
    
    async def calculate_confidence_scores(self, visual_analysis: ImageAnalysisResult,
                                        ocr_result: Optional[OCRResult],
                                        diagrams: List[EducationalDiagram],
                                        categories: List[VisualCategory]) -> float:
        """Calculate overall confidence score for visual content interpretation."""
        try:
            confidence_factors = []
            
            # OCR confidence
            if ocr_result and ocr_result.text.strip():
                confidence_factors.append(ocr_result.confidence * 0.3)
            
            # Visual analysis confidence
            if visual_analysis:
                confidence_factors.append(visual_analysis.confidence_score * 0.4)
            
            # Diagram detection confidence
            if diagrams:
                avg_diagram_confidence = sum(d.confidence for d in diagrams) / len(diagrams)
                confidence_factors.append(avg_diagram_confidence * 0.2)
            
            # Category confidence
            if categories:
                avg_category_confidence = sum(c.confidence for c in categories) / len(categories)
                confidence_factors.append(avg_category_confidence * 0.1)
            
            # Calculate weighted average
            if confidence_factors:
                overall_confidence = sum(confidence_factors) / len(confidence_factors)
                return min(overall_confidence, 1.0)
            
            return 0.5  # Default confidence
            
        except Exception as e:
            logger.error(f"Error calculating confidence scores: {e}")
            return 0.3


# Global instance
image_agent = ImageAgent()