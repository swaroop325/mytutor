"""
Video Agent - Specialized processor for video files with multi-modal processing
Handles: MP4, AVI, MOV, MKV, WMV, FLV, WebM, M4V files
Enhanced with intelligent keyframe selection, scene change detection, and OCR
"""
import os
import json
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import cv2
import boto3
from strands import Agent
import base64
import tempfile
import numpy as np
from datetime import datetime
import logging
import asyncio

try:
    from ..config.model_manager import model_config_manager
except ImportError:
    # Fallback for when not running as package
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from config.model_manager import model_config_manager

logger = logging.getLogger(__name__)


class VideoAgent:
    """Specialized agent for processing video files with multi-modal capabilities."""
    
    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self.agent = Agent()
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=region)
        self.textract_client = boto3.client('textract', region_name=region)
        

        
        self.supported_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v']
        
        # Scene change detection parameters
        self.scene_change_threshold = 0.3  # Threshold for detecting scene changes
        self.min_keyframe_interval = 2.0   # Minimum seconds between keyframes
        self.max_keyframes = 15            # Maximum number of keyframes to extract
        
        # Audio processing parameters
        self.audio_segment_duration = 30.0  # Seconds per audio segment for analysis
    
    def _resolve_file_path(self, file_path: Path) -> Path:
        """Resolve file path relative to project structure."""
        print(f"🔍 Video Agent - Resolving file path: {file_path}")
        print(f"🔍 Video Agent - Current working directory: {Path.cwd()}")
        
        # If the path exists as-is, use it
        if file_path.exists():
            print(f"✅ Video Agent - Found file at original path: {file_path}")
            return file_path
        
        # Try in backend directory (most common case)
        backend_path = Path("backend") / file_path
        print(f"🔍 Video Agent - Trying backend path: {backend_path}")
        if backend_path.exists():
            print(f"✅ Video Agent - Found file at backend path: {backend_path}")
            return backend_path
        
        # Try relative to backend directory (from agent directory)
        backend_relative_path = Path("../backend") / file_path
        print(f"🔍 Video Agent - Trying backend relative path: {backend_relative_path}")
        if backend_relative_path.exists():
            print(f"✅ Video Agent - Found file at backend relative path: {backend_relative_path}")
            return backend_relative_path
        
        # Try absolute path from project root
        project_root_path = Path("..") / file_path
        print(f"🔍 Video Agent - Trying project root path: {project_root_path}")
        if project_root_path.exists():
            print(f"✅ Video Agent - Found file at project root path: {project_root_path}")
            return project_root_path
        
        # Return original path if nothing works
        print(f"❌ Video Agent - Could not resolve file path, using original: {file_path}")
        return file_path
    
    def can_process(self, file_path: str) -> bool:
        """Check if this agent can process the given file."""
        return any(file_path.lower().endswith(ext) for ext in self.supported_extensions)
    
    async def process_file(self, file_path: str, user_id: str) -> Dict[str, Any]:
        """Process a video file."""
        try:
            print(f"🎬 VIDEO Agent processing: {file_path}")
            logger.info(f"Starting video processing for: {file_path}")
            
            # Check if file exists first
            if not os.path.exists(file_path):
                error_msg = f"Video file not found: {file_path}"
                print(f"❌ {error_msg}")
                logger.error(error_msg)
                return {
                    "agent_type": "video",
                    "file_path": file_path,
                    "status": "error",
                    "error": error_msg
                }
            
            print(f"✅ Video file exists: {file_path} ({os.path.getsize(file_path)} bytes)")
            
            # Extract video metadata and frames
            print("🔍 Starting video content extraction...")
            video_data = await self._extract_video_content(file_path)
            print("✅ Video content extraction completed")
            logger.info("Video content extraction completed")
            
            # Analyze content with AI (using frames)
            print("🔍 Starting AI content analysis...")
            analysis = await self._analyze_content(video_data, file_path)
            print("✅ AI content analysis completed")
            
            # Prepare result
            result = {
                "agent_type": "video",
                "file_path": file_path,
                "status": "completed",
                "content": {
                    "duration": video_data['metadata']['duration'],
                    "fps": video_data['metadata']['fps'],
                    "resolution": video_data['metadata']['resolution'],
                    "frame_count": video_data['metadata']['frame_count'],
                    "key_frames": len(video_data['frames']),
                    "frames_base64": video_data['frames'][:3]  # First 3 frames only
                },
                "analysis": analysis,
                "metadata": {
                    **video_data['metadata'],
                    "processed_by": "video_agent"
                }
            }
            
            print(f"✅ VIDEO Agent completed: {file_path} ({video_data['metadata']['duration']:.1f}s)")
            return result
            
        except Exception as e:
            logger.error(f"VIDEO Agent error processing {file_path}: {e}", exc_info=True)
            print(f"❌ VIDEO Agent error processing {file_path}: {e}")
            return {
                "agent_type": "video",
                "file_path": file_path,
                "status": "error",
                "error": str(e)
            }
    
    async def _extract_video_content(self, file_path: str) -> Dict[str, Any]:
        """Extract frames and metadata from video with intelligent keyframe selection."""
        try:
            # Resolve the file path
            resolved_path = self._resolve_file_path(Path(file_path))
            print(f"🎬 Video agent processing: {resolved_path}")
            
            if not resolved_path.exists():
                raise FileNotFoundError(f"Video file not found: {resolved_path}")
            
            # Open video file
            cap = cv2.VideoCapture(str(resolved_path))
            
            if not cap.isOpened():
                raise Exception(f"Could not open video file: {file_path}")
            
            # Get video metadata
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps if fps > 0 else 0
            
            metadata = {
                "duration": duration,
                "fps": fps,
                "frame_count": frame_count,
                "resolution": f"{width}x{height}",
                "width": width,
                "height": height,
                "file_size": os.path.getsize(resolved_path),
                "file_type": Path(file_path).suffix.lower()
            }
            
            # Extract intelligent keyframes using scene change detection
            print("🔍 Extracting keyframes...")
            keyframes = await self._extract_intelligent_keyframes(cap, fps, frame_count, width, height)
            print(f"✅ Extracted {len(keyframes)} keyframes")
            
            # Detect slides and presentations in keyframes
            print("🔍 Analyzing slides and presentations...")
            slide_analysis = await self._detect_slides_and_presentations(keyframes)
            print("✅ Slide analysis completed")
            
            # Extract text from frames using OCR
            print("🔍 Extracting text from frames...")
            ocr_results = await self._extract_text_from_frames(keyframes)
            print(f"✅ OCR completed for {len(ocr_results)} frames")
            
            # Extract and analyze audio content (with timeout protection)
            print("🔍 Extracting and analyzing audio...")
            try:
                # Set a reasonable timeout for audio processing
                audio_analysis = await asyncio.wait_for(
                    self._extract_and_analyze_audio(resolved_path, duration),
                    timeout=200  # 3 minutes max for audio processing
                )
                print(f"✅ Audio analysis completed (extracted: {audio_analysis.get('audio_extracted', False)})")
            except asyncio.TimeoutError:
                print("⚠️ Audio processing timed out - continuing with video-only processing")
                audio_analysis = self._create_empty_audio_analysis()
            except Exception as e:
                print(f"⚠️ Audio processing failed: {e} - continuing with video-only processing")
                audio_analysis = self._create_empty_audio_analysis()
            
            # Create timeline correlation between visual and audio content
            print("🔍 Creating timeline correlation...")
            timeline_correlation = await self._create_timeline_correlation(
                keyframes, ocr_results, audio_analysis, duration
            )
            print("✅ Timeline correlation completed")
            
            cap.release()
            
            return {
                "metadata": metadata,
                "keyframes": keyframes,
                "slide_analysis": slide_analysis,
                "ocr_results": ocr_results,
                "audio_analysis": audio_analysis,
                "timeline_correlation": timeline_correlation,
                "frames": keyframes  # Backward compatibility
            }
            
        except Exception as e:
            logger.error(f"Error processing video {file_path}: {e}", exc_info=True)
            print(f"❌ Video content extraction failed: {e}")
            return {
                "metadata": {
                    "duration": 0,
                    "fps": 0,
                    "frame_count": 0,
                    "resolution": "unknown",
                    "file_size": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                    "file_type": Path(file_path).suffix.lower(),
                    "error": str(e)
                },
                "keyframes": [],
                "slide_analysis": {},
                "ocr_results": [],
                "audio_analysis": self._create_empty_audio_analysis(),
                "timeline_correlation": {},
                "frames": []
            }
    
    async def _extract_intelligent_keyframes(self, cap: cv2.VideoCapture, fps: float, 
                                           frame_count: int, width: int, height: int) -> List[Dict[str, Any]]:
        """Extract keyframes using scene change detection and content analysis."""
        try:
            keyframes = []
            prev_frame = None
            last_keyframe_time = -self.min_keyframe_interval
            
            # Sample frames for scene change detection
            sample_interval = max(1, int(fps * 0.5))  # Sample every 0.5 seconds
            
            for frame_idx in range(0, frame_count, sample_interval):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if not ret:
                    continue
                
                current_time = frame_idx / fps if fps > 0 else 0
                
                # Resize frame for processing
                if width > 512:
                    scale = 512 / width
                    new_width = 512
                    new_height = int(height * scale)
                    frame_resized = cv2.resize(frame, (new_width, new_height))
                else:
                    frame_resized = frame.copy()
                
                # Convert to grayscale for scene change detection
                gray_frame = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2GRAY)
                
                # Check for scene change
                is_scene_change = False
                if prev_frame is not None:
                    # Calculate histogram difference
                    hist_diff = self._calculate_histogram_difference(prev_frame, gray_frame)
                    is_scene_change = hist_diff > self.scene_change_threshold
                
                # Add keyframe if it's a scene change or first frame
                should_add_keyframe = (
                    prev_frame is None or  # First frame
                    is_scene_change or     # Scene change detected
                    (current_time - last_keyframe_time >= self.min_keyframe_interval and 
                     len(keyframes) < self.max_keyframes)  # Time-based sampling
                )
                
                if should_add_keyframe and current_time - last_keyframe_time >= self.min_keyframe_interval:
                    # Convert to base64
                    _, buffer = cv2.imencode('.jpg', frame_resized, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    frame_base64 = base64.b64encode(buffer).decode('utf-8')
                    
                    keyframe_data = {
                        "timestamp": current_time,
                        "frame_number": frame_idx,
                        "base64": frame_base64,
                        "scene_change": is_scene_change,
                        "histogram_diff": hist_diff if prev_frame is not None else 0.0
                    }
                    
                    keyframes.append(keyframe_data)
                    last_keyframe_time = current_time
                
                prev_frame = gray_frame
                
                # Stop if we have enough keyframes
                if len(keyframes) >= self.max_keyframes:
                    break
            
            # Ensure we have at least one keyframe (first frame)
            if not keyframes and frame_count > 0:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
                if ret:
                    if width > 512:
                        scale = 512 / width
                        new_width = 512
                        new_height = int(height * scale)
                        frame = cv2.resize(frame, (new_width, new_height))
                    
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    frame_base64 = base64.b64encode(buffer).decode('utf-8')
                    
                    keyframes.append({
                        "timestamp": 0.0,
                        "frame_number": 0,
                        "base64": frame_base64,
                        "scene_change": False,
                        "histogram_diff": 0.0
                    })
            
            logger.info(f"Extracted {len(keyframes)} intelligent keyframes")
            return keyframes
            
        except Exception as e:
            logger.error(f"Error extracting intelligent keyframes: {e}")
            return []
    
    def _calculate_histogram_difference(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """Calculate histogram difference between two frames for scene change detection."""
        try:
            # Calculate histograms
            hist1 = cv2.calcHist([frame1], [0], None, [256], [0, 256])
            hist2 = cv2.calcHist([frame2], [0], None, [256], [0, 256])
            
            # Normalize histograms
            cv2.normalize(hist1, hist1, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
            cv2.normalize(hist2, hist2, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
            
            # Calculate correlation coefficient (higher = more similar)
            correlation = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
            
            # Convert to difference (1 - correlation, so higher = more different)
            return 1.0 - correlation
            
        except Exception as e:
            logger.error(f"Error calculating histogram difference: {e}")
            return 0.0
    
    async def _detect_slides_and_presentations(self, keyframes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect slides and presentation content in keyframes."""
        try:
            slide_indicators = []
            presentation_features = {
                "has_text_slides": False,
                "has_bullet_points": False,
                "has_charts_graphs": False,
                "slide_transitions": 0,
                "estimated_slide_count": 0
            }
            
            for i, keyframe in enumerate(keyframes):
                # Decode frame for analysis
                frame_data = base64.b64decode(keyframe['base64'])
                frame_array = np.frombuffer(frame_data, dtype=np.uint8)
                frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
                
                if frame is None:
                    continue
                
                # Analyze frame for slide characteristics
                slide_features = self._analyze_frame_for_slides(frame)
                
                slide_indicator = {
                    "timestamp": keyframe['timestamp'],
                    "frame_number": keyframe['frame_number'],
                    "is_likely_slide": slide_features['is_slide'],
                    "text_density": slide_features['text_density'],
                    "has_bullet_points": slide_features['has_bullets'],
                    "background_uniformity": slide_features['background_uniformity'],
                    "edge_density": slide_features['edge_density']
                }
                
                slide_indicators.append(slide_indicator)
                
                # Update presentation features
                if slide_features['is_slide']:
                    presentation_features["estimated_slide_count"] += 1
                    presentation_features["has_text_slides"] = True
                
                if slide_features['has_bullets']:
                    presentation_features["has_bullet_points"] = True
                
                # Count slide transitions (scene changes that are likely slides)
                if keyframe.get('scene_change', False) and slide_features['is_slide']:
                    presentation_features["slide_transitions"] += 1
            
            return {
                "slide_indicators": slide_indicators,
                "presentation_features": presentation_features,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error detecting slides and presentations: {e}")
            return {"slide_indicators": [], "presentation_features": {}}
    
    def _analyze_frame_for_slides(self, frame: np.ndarray) -> Dict[str, Any]:
        """Analyze a single frame for slide characteristics."""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            height, width = gray.shape
            
            # Calculate background uniformity (slides often have uniform backgrounds)
            background_uniformity = self._calculate_background_uniformity(gray)
            
            # Calculate edge density (slides often have clean, defined edges)
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / (width * height)
            
            # Estimate text density using edge patterns
            text_density = self._estimate_text_density(gray)
            
            # Check for bullet point patterns
            has_bullets = self._detect_bullet_patterns(gray)
            
            # Determine if this looks like a slide
            is_slide = (
                background_uniformity > 0.7 and  # Uniform background
                edge_density > 0.02 and         # Some structured content
                text_density > 0.1              # Some text content
            )
            
            return {
                "is_slide": is_slide,
                "background_uniformity": background_uniformity,
                "edge_density": edge_density,
                "text_density": text_density,
                "has_bullets": has_bullets
            }
            
        except Exception as e:
            logger.error(f"Error analyzing frame for slides: {e}")
            return {
                "is_slide": False,
                "background_uniformity": 0.0,
                "edge_density": 0.0,
                "text_density": 0.0,
                "has_bullets": False
            }
    
    def _calculate_background_uniformity(self, gray_frame: np.ndarray) -> float:
        """Calculate how uniform the background is (higher = more uniform)."""
        try:
            # Calculate standard deviation of pixel values
            std_dev = np.std(gray_frame)
            # Normalize to 0-1 range (lower std_dev = more uniform)
            uniformity = max(0.0, 1.0 - (std_dev / 128.0))
            return uniformity
        except:
            return 0.0
    
    def _estimate_text_density(self, gray_frame: np.ndarray) -> float:
        """Estimate text density in the frame."""
        try:
            # Use morphological operations to detect text-like regions
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            
            # Apply morphological gradient to highlight text edges
            morph_grad = cv2.morphologyEx(gray_frame, cv2.MORPH_GRADIENT, kernel)
            
            # Threshold to get text regions
            _, text_regions = cv2.threshold(morph_grad, 30, 255, cv2.THRESH_BINARY)
            
            # Calculate density
            text_pixels = np.sum(text_regions > 0)
            total_pixels = gray_frame.shape[0] * gray_frame.shape[1]
            
            return text_pixels / total_pixels
            
        except:
            return 0.0
    
    def _detect_bullet_patterns(self, gray_frame: np.ndarray) -> bool:
        """Detect bullet point patterns in the frame."""
        try:
            # Look for small circular or square patterns that could be bullets
            # This is a simplified detection - could be enhanced with more sophisticated methods
            
            # Apply Hough Circle detection for circular bullets
            circles = cv2.HoughCircles(
                gray_frame, cv2.HOUGH_GRADIENT, dp=1, minDist=20,
                param1=50, param2=30, minRadius=2, maxRadius=15
            )
            
            if circles is not None and len(circles[0]) > 2:
                return True
            
            # Look for repeated small rectangular patterns (square bullets)
            # This is a basic implementation
            edges = cv2.Canny(gray_frame, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            small_rectangles = 0
            for contour in contours:
                area = cv2.contourArea(contour)
                if 10 < area < 100:  # Small rectangular areas
                    x, y, w, h = cv2.boundingRect(contour)
                    aspect_ratio = w / h if h > 0 else 0
                    if 0.5 < aspect_ratio < 2.0:  # Roughly square
                        small_rectangles += 1
            
            return small_rectangles > 3
            
        except:
            return False
    
    async def _extract_text_from_frames(self, keyframes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract text from video frames using local OCR."""
        try:
            ocr_results = []
            
            for keyframe in keyframes:
                try:
                    # Decode frame
                    frame_data = base64.b64decode(keyframe['base64'])
                    frame_array = np.frombuffer(frame_data, dtype=np.uint8)
                    frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
                    
                    if frame is None:
                        continue
                    
                    # Use local OCR (try multiple methods)
                    extracted_text, confidence = await self._extract_text_with_local_ocr(frame)
                    
                    # Split text into blocks (lines)
                    text_blocks = [line.strip() for line in extracted_text.split('\n') if line.strip()]
                    
                    ocr_result = {
                        "timestamp": keyframe['timestamp'],
                        "frame_number": keyframe['frame_number'],
                        "extracted_text": extracted_text,
                        "text_blocks": text_blocks,
                        "confidence_score": confidence,
                        "text_block_count": len(text_blocks),
                        "method": "local_ocr"
                    }
                    
                    ocr_results.append(ocr_result)
                    
                except Exception as e:
                    logger.warning(f"Local OCR failed for frame at {keyframe['timestamp']}s: {e}")
                    # Add empty result to maintain frame correspondence
                    ocr_results.append({
                        "timestamp": keyframe['timestamp'],
                        "frame_number": keyframe['frame_number'],
                        "extracted_text": "",
                        "text_blocks": [],
                        "confidence_score": 0.0,
                        "text_block_count": 0,
                        "error": str(e)
                    })
            
            logger.info(f"Completed local OCR for {len(ocr_results)} frames")
            return ocr_results
            
        except Exception as e:
            logger.error(f"Error extracting text from frames: {e}")
            return []
    
    async def _extract_text_with_local_ocr(self, frame: np.ndarray) -> Tuple[str, float]:
        """Extract text from a frame using local OCR methods."""
        try:
            # Try Tesseract OCR first (if available)
            try:
                import pytesseract
                
                # Preprocess image for better OCR
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Apply threshold to get better contrast
                _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                # Extract text with confidence
                data = pytesseract.image_to_data(thresh, output_type=pytesseract.Output.DICT)
                
                # Filter out low-confidence text
                text_parts = []
                confidences = []
                
                for i, conf in enumerate(data['conf']):
                    if int(conf) > 30:  # Confidence threshold
                        text = data['text'][i].strip()
                        if text:
                            text_parts.append(text)
                            confidences.append(int(conf))
                
                extracted_text = ' '.join(text_parts)
                avg_confidence = np.mean(confidences) / 100.0 if confidences else 0.0  # Convert to 0-1 range
                
                return extracted_text, avg_confidence
                
            except ImportError:
                logger.info("Tesseract not available, trying EasyOCR")
            
            # Try EasyOCR as fallback
            try:
                import easyocr
                
                # Initialize EasyOCR reader (English)
                reader = easyocr.Reader(['en'], gpu=False)  # Use CPU to avoid GPU dependencies
                
                # Extract text
                results = reader.readtext(frame)
                
                # Process results
                text_parts = []
                confidences = []
                
                for (bbox, text, confidence) in results:
                    if confidence > 0.3:  # Confidence threshold
                        text_parts.append(text.strip())
                        confidences.append(confidence)
                
                extracted_text = ' '.join(text_parts)
                avg_confidence = np.mean(confidences) if confidences else 0.0
                
                return extracted_text, avg_confidence
                
            except ImportError:
                logger.warning("No OCR libraries available (tesseract, easyocr)")
            
            # If no OCR libraries available, return empty result
            return "", 0.0
            
        except Exception as e:
            logger.error(f"Local OCR extraction failed: {e}")
            return "", 0.0

    async def _analyze_content(self, video_data: Dict[str, Any], file_path: str) -> Dict[str, Any]:
        """Analyze video content using AI with enhanced multi-modal analysis."""
        try:
            metadata = video_data['metadata']
            keyframes = video_data.get('keyframes', [])
            slide_analysis = video_data.get('slide_analysis', {})
            ocr_results = video_data.get('ocr_results', [])
            audio_analysis = video_data.get('audio_analysis', {})
            timeline_correlation = video_data.get('timeline_correlation', {})
            
            # Get optimal model for video analysis
            model_spec = model_config_manager.get_model_for_agent("video", "video")
            if not model_spec:
                raise Exception("No suitable model found for video analysis")
            
            # Prepare enhanced content for analysis
            content_parts = [
                {
                    "type": "text",
                    "text": f"""
Analyze this video file with enhanced multi-modal processing:

File: {Path(file_path).name}
Duration: {metadata.get('duration', 0):.1f} seconds
Resolution: {metadata.get('resolution', 'Unknown')}
FPS: {metadata.get('fps', 0):.1f}
Intelligent keyframes extracted: {len(keyframes)}

SLIDE ANALYSIS:
- Estimated slide count: {slide_analysis.get('presentation_features', {}).get('estimated_slide_count', 0)}
- Has text slides: {slide_analysis.get('presentation_features', {}).get('has_text_slides', False)}
- Has bullet points: {slide_analysis.get('presentation_features', {}).get('has_bullet_points', False)}
- Slide transitions: {slide_analysis.get('presentation_features', {}).get('slide_transitions', 0)}

OCR TEXT EXTRACTED:
{self._format_ocr_text(ocr_results)}

AUDIO TRANSCRIPTION:
{self._format_audio_transcript(audio_analysis)}

SPEAKER ANALYSIS:
{self._format_speaker_analysis(audio_analysis)}

TIMELINE CORRELATION:
- Total multimodal events: {timeline_correlation.get('total_events', 0)}
- Events per minute: {timeline_correlation.get('events_per_minute', 0):.1f}
- Presentation style: {timeline_correlation.get('correlations', {}).get('presentation_flow', {}).get('presentation_style', 'unknown')}

Please provide comprehensive multi-modal analysis including:
1. Video type and format (educational, presentation, tutorial, lecture, etc.)
2. Content structure and organization
3. Key topics and learning objectives identified
4. Educational value and difficulty level
5. Presentation quality and visual design
6. Text content analysis from OCR
7. Scene progression and narrative flow
8. Target audience and recommended use cases
9. Learning outcomes and assessment potential
10. Technical quality and accessibility
11. Audio-visual synchronization and correlation
12. Speaker engagement and presentation effectiveness
13. Multi-modal learning opportunities
14. Content accessibility across different learning styles

Format as structured JSON with detailed insights.
"""
                }
            ]
            
            # Add keyframe images for analysis (limit to avoid token limits)
            max_frames_for_analysis = min(5, len(keyframes))
            for i in range(max_frames_for_analysis):
                keyframe = keyframes[i]
                content_parts.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": keyframe['base64']
                    }
                })
            
            # Use the configured model
            response = self.bedrock_client.invoke_model(
                modelId=model_spec.model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": model_spec.max_tokens,
                    "temperature": model_spec.temperature,
                    "messages": [
                        {
                            "role": "user",
                            "content": content_parts
                        }
                    ]
                })
            )
            
            result = json.loads(response['body'].read())
            analysis_text = result['content'][0]['text']
            
            return {
                "ai_analysis": analysis_text,
                "content_type": "video_file",
                "processing_method": "intelligent_keyframe_extraction_and_multimodal_analysis",
                "keyframes_analyzed": len(keyframes),
                "frames_with_text": len([r for r in ocr_results if r.get('extracted_text', '').strip()]),
                "slide_detection": slide_analysis.get('presentation_features', {}),
                "audio_transcribed": audio_analysis.get('audio_extracted', False),
                "speaker_count": audio_analysis.get('speaker_analysis', {}).get('speaker_count', 0),
                "multimodal_events": timeline_correlation.get('total_events', 0),
                "duration_seconds": metadata.get('duration', 0),
                "model_used": model_spec.model_id,
                "scene_changes_detected": len([k for k in keyframes if k.get('scene_change', False)])
            }
            
        except Exception as e:
            logger.error(f"Error analyzing video content: {e}")
            
            # Try fallback model
            try:
                fallback_model = model_config_manager.get_fallback_model("video", model_spec.model_id if 'model_spec' in locals() else "")
                if fallback_model:
                    logger.info(f"Attempting analysis with fallback model: {fallback_model.model_id}")
                    # Simplified analysis with fallback
                    return await self._analyze_with_fallback(video_data, file_path, fallback_model)
            except Exception as fallback_error:
                logger.error(f"Fallback analysis also failed: {fallback_error}")
            
            return {
                "ai_analysis": f"Analysis failed: {str(e)}",
                "content_type": "video_file",
                "processing_method": "metadata_extraction_only",
                "keyframes_analyzed": len(keyframes),
                "duration_seconds": metadata.get('duration', 0),
                "error": str(e)
            }
    
    def _format_ocr_text(self, ocr_results: List[Dict[str, Any]]) -> str:
        """Format OCR results for analysis."""
        if not ocr_results:
            return "No text extracted from frames."
        
        formatted_text = []
        for result in ocr_results:
            text = result.get('extracted_text', '').strip()
            if text:
                timestamp = result.get('timestamp', 0)
                formatted_text.append(f"[{timestamp:.1f}s] {text}")
        
        if not formatted_text:
            return "No readable text found in video frames."
        
        return '\n'.join(formatted_text[:10])  # Limit to first 10 text blocks
    
    def _format_audio_transcript(self, audio_analysis: Dict[str, Any]) -> str:
        """Format audio transcription for analysis."""
        transcription = audio_analysis.get('transcription', {})
        
        if not transcription.get('transcript', '').strip():
            return "No audio transcription available."
        
        segments = transcription.get('segments', [])
        if not segments:
            return f"Transcript: {transcription['transcript'][:500]}..."
        
        formatted_segments = []
        for segment in segments[:5]:  # Limit to first 5 segments
            start_time = segment.get('start_time', 0)
            text = segment.get('text', '').strip()
            confidence = segment.get('confidence', 0)
            
            if text:
                formatted_segments.append(f"[{start_time:.1f}s] {text} (confidence: {confidence:.2f})")
        
        return '\n'.join(formatted_segments)
    
    def _format_speaker_analysis(self, audio_analysis: Dict[str, Any]) -> str:
        """Format speaker analysis for AI analysis."""
        speaker_analysis = audio_analysis.get('speaker_analysis', {})
        
        if not speaker_analysis.get('speakers'):
            return "No speaker analysis available."
        
        speakers = speaker_analysis.get('speakers', [])
        speaker_count = speaker_analysis.get('speaker_count', 0)
        
        if speaker_count == 0:
            return "No speakers detected."
        
        formatted_info = [f"Total speakers detected: {speaker_count}"]
        
        for speaker in speakers[:3]:  # Limit to first 3 speakers
            speaker_id = speaker.get('speaker_id', 'Unknown')
            duration = speaker.get('total_duration', 0)
            segments = speaker.get('segment_count', 0)
            
            formatted_info.append(f"- {speaker_id}: {duration:.1f}s speaking time, {segments} segments")
        
        return '\n'.join(formatted_info)
    
    async def _analyze_with_fallback(self, video_data: Dict[str, Any], file_path: str, 
                                   fallback_model: Any) -> Dict[str, Any]:
        """Perform simplified analysis with fallback model."""
        try:
            metadata = video_data['metadata']
            keyframes = video_data.get('keyframes', [])
            
            # Simplified analysis without vision capabilities
            content_text = f"""
Analyze this video file (metadata only):

File: {Path(file_path).name}
Duration: {metadata.get('duration', 0):.1f} seconds
Resolution: {metadata.get('resolution', 'Unknown')}
Keyframes extracted: {len(keyframes)}

Provide basic analysis of video characteristics and potential educational value.
"""
            
            response = self.bedrock_client.invoke_model(
                modelId=fallback_model.model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": fallback_model.max_tokens,
                    "temperature": fallback_model.temperature,
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": content_text}]
                        }
                    ]
                })
            )
            
            result = json.loads(response['body'].read())
            analysis_text = result['content'][0]['text']
            
            return {
                "ai_analysis": analysis_text,
                "content_type": "video_file",
                "processing_method": "fallback_metadata_analysis",
                "keyframes_analyzed": len(keyframes),
                "duration_seconds": metadata.get('duration', 0),
                "model_used": fallback_model.model_id,
                "fallback_used": True
            }
            
        except Exception as e:
            logger.error(f"Fallback analysis failed: {e}")
            return {
                "ai_analysis": f"All analysis methods failed: {str(e)}",
                "content_type": "video_file",
                "processing_method": "failed",
                "error": str(e)
            }
    
    async def _extract_and_analyze_audio(self, video_path: Path, duration: float) -> Dict[str, Any]:
        """Extract audio from video and perform transcription and speaker analysis."""
        try:
            # Check if FFmpeg is available first
            try:
                import subprocess
                result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
                if result.returncode != 0:
                    raise FileNotFoundError("FFmpeg not working properly")
            except (FileNotFoundError, subprocess.TimeoutExpired):
                logger.info("FFmpeg not available, skipping audio extraction for video")
                print("ℹ️ FFmpeg not available - video will be processed without audio transcription")
                print("💡 To enable audio processing from videos, install FFmpeg:")
                print("   macOS: brew install ffmpeg")
                print("   Ubuntu: sudo apt install ffmpeg")
                print("   Windows: Download from https://ffmpeg.org/download.html")
                return self._create_empty_audio_analysis()
            
            # Extract audio from video using ffmpeg
            audio_file = None
            try:
                # Create temporary audio file
                audio_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                audio_path = audio_file.name
                audio_file.close()
                
                # Extract audio using ffmpeg
                cmd = [
                    'ffmpeg', '-i', str(video_path), 
                    '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
                    '-y', audio_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode != 0:
                    logger.warning(f"FFmpeg extraction failed: {result.stderr}")
                    return self._create_empty_audio_analysis()
                
                # Perform transcription and speaker analysis
                transcription_result = await self._transcribe_audio(audio_path, duration)
                speaker_analysis = await self._analyze_speakers(transcription_result)
                
                return {
                    "transcription": transcription_result,
                    "speaker_analysis": speaker_analysis,
                    "audio_extracted": True,
                    "processing_method": f"ffmpeg_extraction_{transcription_result.get('processing_method', 'unknown')}"
                }
                
            except subprocess.TimeoutExpired:
                logger.warning("Audio extraction timed out")
                return self._create_empty_audio_analysis()
            except FileNotFoundError:
                logger.info("FFmpeg not found, continuing video processing without audio extraction")
                print("ℹ️ FFmpeg not available - video will be processed without audio transcription")
                return self._create_empty_audio_analysis()
            except Exception as e:
                logger.warning(f"Audio extraction failed: {e}")
                return self._create_empty_audio_analysis()
            finally:
                # Clean up temporary audio file
                if audio_file and os.path.exists(audio_file.name):
                    try:
                        os.unlink(audio_file.name)
                    except:
                        pass
                        
        except Exception as e:
            logger.error(f"Error in audio extraction and analysis: {e}")
            return self._create_empty_audio_analysis()
    
    def _create_empty_audio_analysis(self) -> Dict[str, Any]:
        """Create empty audio analysis structure when audio processing fails."""
        return {
            "transcription": {
                "transcript": "",
                "segments": [],
                "confidence": 0.0
            },
            "speaker_analysis": {
                "speakers": [],
                "speaker_segments": [],
                "speaker_count": 0
            },
            "audio_extracted": False,
            "processing_method": "audio_extraction_failed"
        }
    
    async def _transcribe_with_local_whisper(self, audio_path: str, duration: float) -> Optional[Dict[str, Any]]:
        """Transcribe audio using local OpenAI Whisper (fast, no S3 required)."""
        try:
            import whisper
            
            # Load Whisper model (optimized for speed vs accuracy)
            if not hasattr(self, 'whisper_model'):
                # Use 'base' model for good balance, 'small' for faster processing
                model_size = os.getenv('WHISPER_MODEL_SIZE', 'base')  # base, small, medium, large
                print(f"🎵 Loading Whisper model for video: {model_size}")
                self.whisper_model = whisper.load_model(model_size)
                logger.info(f"Loaded local Whisper model for video: {model_size}")
            
            print(f"🎵 Transcribing video audio with local Whisper: {audio_path}")
            
            # Transcribe with optimized settings for speed
            result = self.whisper_model.transcribe(
                audio_path,
                word_timestamps=True,
                verbose=False,
                temperature=0.0,  # More deterministic, faster
                best_of=1,        # Faster inference
                beam_size=1,      # Faster beam search
                fp16=True         # Use half precision for speed (if supported)
            )
            
            # Convert Whisper format to our expected format
            transcript_text = result.get('text', '')
            segments = []
            
            # Process Whisper segments
            for segment in result.get('segments', []):
                segments.append({
                    'start_time': segment.get('start', 0),
                    'end_time': segment.get('end', 0),
                    'text': segment.get('text', '').strip(),
                    'confidence': max(0.0, min(1.0, segment.get('avg_logprob', -1.0) + 1.0))  # Convert log prob to confidence
                })
            
            print(f"✅ Local Whisper video transcription completed: {len(transcript_text)} chars, {len(segments)} segments")
            logger.info(f"Local Whisper video transcription completed for {audio_path}")
            
            return {
                'transcript': transcript_text,
                'segments': segments,
                'confidence': sum(seg['confidence'] for seg in segments) / len(segments) if segments else 0.5,
                'processing_method': 'local_whisper'
            }
            
        except ImportError:
            print("⚠️ OpenAI Whisper not available for video transcription")
            logger.info("OpenAI Whisper not available for video transcription")
            return None
        except Exception as e:
            print(f"❌ Local Whisper video transcription failed: {e}")
            logger.error(f"Local Whisper video transcription failed for {audio_path}: {e}")
            return None
    
    async def _transcribe_with_bedrock_audio(self, audio_path: str, duration: float) -> Optional[Dict[str, Any]]:
        """Transcribe video audio using Bedrock audio models (context-aware, integrated)."""
        try:
            print(f"🤖 Transcribing video audio with Bedrock audio models...")
            
            # Check file size and duration - Bedrock has limits
            file_size_mb = os.path.getsize(audio_path) / (1024 * 1024) if os.path.exists(audio_path) else 0
            if file_size_mb > 25:  # Bedrock audio limit is typically around 25MB
                print(f"⚠️ Audio file too large for Bedrock ({file_size_mb:.1f}MB > 25MB)")
                return None
            
            if duration > 600:  # 10 minutes - practical limit for good results
                print(f"⚠️ Audio too long for Bedrock ({duration:.1f}s > 600s)")
                return None
            
            # Read audio file and encode to base64
            with open(audio_path, 'rb') as audio_file:
                audio_data = audio_file.read()
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Audio extracted from video is typically WAV
            media_type = 'audio/wav'
            
            # Use Claude 3.5 Sonnet with audio capabilities for video content
            prompt = f"""
Please transcribe this audio extracted from a video (duration: {duration:.1f}s) and provide:
1. Full transcript text
2. Key topics and concepts discussed
3. Educational content type (lecture, tutorial, presentation, etc.)
4. Speaker analysis and speaking patterns
5. Confidence level

This appears to be educational video content. Focus on:
- Technical terms and concepts
- Learning objectives
- Key explanations and examples
- Question/answer segments

Format the response as JSON:
{{
    "transcript": "full transcription text",
    "topics": ["topic1", "topic2"],
    "content_type": "lecture/tutorial/presentation/discussion",
    "key_concepts": ["concept1", "concept2"],
    "speakers": [{{"id": "speaker1", "role": "instructor/student", "speaking_time": "percentage"}}],
    "educational_value": "assessment of educational content and learning objectives",
    "confidence": 0.95
}}
"""
            
            # Prepare the message with audio
            message_content = [
                {
                    "type": "text",
                    "text": prompt
                },
                {
                    "type": "audio",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": audio_base64
                    }
                }
            ]
            
            # Call Bedrock with audio
            response = self.bedrock_client.invoke_model(
                modelId="us.anthropic.claude-3-5-sonnet-20241022-v2:0",  # Latest Claude with audio
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4000,
                    "temperature": 0.1,
                    "messages": [
                        {
                            "role": "user", 
                            "content": message_content
                        }
                    ]
                })
            )
            
            result = json.loads(response['body'].read())
            response_text = result['content'][0]['text']
            
            # Try to parse JSON response
            try:
                parsed_result = json.loads(response_text)
                
                # Convert to our expected format
                segments = []
                transcript_text = parsed_result.get('transcript', '')
                
                # Create basic segments (Bedrock doesn't provide timestamps)
                if transcript_text:
                    # Split into sentences for basic segmentation
                    sentences = transcript_text.split('. ')
                    segment_duration = duration / len(sentences) if sentences else duration
                    
                    for i, sentence in enumerate(sentences):
                        if sentence.strip():
                            segments.append({
                                'start_time': i * segment_duration,
                                'end_time': (i + 1) * segment_duration,
                                'text': sentence.strip() + ('.' if not sentence.endswith('.') else ''),
                                'confidence': parsed_result.get('confidence', 0.9)
                            })
                
                print(f"✅ Bedrock video audio transcription completed: {len(transcript_text)} chars, {len(segments)} segments")
                
                return {
                    'transcript': transcript_text,
                    'segments': segments,
                    'confidence': parsed_result.get('confidence', 0.9),
                    'topics': parsed_result.get('topics', []),
                    'content_type': parsed_result.get('content_type', 'educational'),
                    'key_concepts': parsed_result.get('key_concepts', []),
                    'educational_value': parsed_result.get('educational_value', ''),
                    'processing_method': 'bedrock_audio'
                }
                
            except json.JSONDecodeError:
                # If JSON parsing fails, use the raw text as transcript
                segments = [{
                    'start_time': 0,
                    'end_time': duration,
                    'text': response_text,
                    'confidence': 0.8
                }]
                
                return {
                    'transcript': response_text,
                    'segments': segments,
                    'confidence': 0.8,
                    'processing_method': 'bedrock_audio_raw'
                }
            
        except Exception as e:
            print(f"❌ Bedrock video audio transcription failed: {e}")
            logger.error(f"Bedrock video audio transcription failed for {audio_path}: {e}")
            return None
    
    async def _transcribe_audio(self, audio_path: str, duration: float) -> Dict[str, Any]:
        """Transcribe audio using Bedrock audio models (context-aware) with local Whisper fallback."""
        try:
            # Primary: Use Bedrock audio models (context-aware, educational focus)
            print(f"🤖 Transcribing video audio with Bedrock audio models...")
            bedrock_result = await self._transcribe_with_bedrock_audio(audio_path, duration)
            
            if bedrock_result and bedrock_result.get('transcript'):
                print(f"✅ Bedrock audio transcription successful for video!")
                return bedrock_result
            
            print(f"⚠️ Bedrock audio failed, trying local Whisper...")
            
            # Fallback: Local Whisper (fast, offline, free)
            whisper_result = await self._transcribe_with_local_whisper(audio_path, duration)
            
            if whisper_result and whisper_result.get('transcript'):
                print(f"✅ Local Whisper transcription successful for video audio!")
                return whisper_result
            
            print(f"❌ Both Bedrock and Whisper failed for video - no transcription available")
            
            # Return empty result structure
            return {"transcript": "", "segments": [], "confidence": 0.0}
            
        except Exception as e:
            logger.error(f"Audio transcription failed: {e}")
            return {"transcript": "", "segments": [], "confidence": 0.0}
    


    

    

    
    async def _analyze_speakers(self, transcription_result: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze speaker information from transcription results."""
        try:
            segments = transcription_result.get('segments', [])
            
            if not segments:
                return {
                    "speakers": [],
                    "speaker_segments": [],
                    "speaker_count": 0
                }
            
            # Use AI to identify speaker changes and characteristics
            model_spec = model_config_manager.get_model_for_agent("video", "text")
            if not model_spec:
                return self._basic_speaker_analysis(segments)
            
            # Prepare transcript text for analysis
            transcript_text = "\n".join([
                f"[{seg['start_time']:.1f}s - {seg['end_time']:.1f}s] {seg['text']}"
                for seg in segments
            ])
            
            analysis_prompt = f"""
Analyze this video transcript for speaker identification and characteristics:

{transcript_text}

Please identify:
1. Approximate number of different speakers
2. Speaker change points (timestamps where speaker likely changes)
3. Speaking patterns and characteristics for each speaker
4. Content themes associated with each speaker
5. Speaker roles (presenter, interviewer, student, etc.)

Format as JSON with speaker segments and characteristics.
"""
            
            response = self.bedrock_client.invoke_model(
                modelId=model_spec.model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2000,
                    "temperature": 0.1,
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": analysis_prompt}]
                        }
                    ]
                })
            )
            
            result = json.loads(response['body'].read())
            ai_analysis = result['content'][0]['text']
            
            # Parse AI analysis and combine with basic analysis
            basic_analysis = self._basic_speaker_analysis(segments)
            
            return {
                **basic_analysis,
                "ai_speaker_analysis": ai_analysis,
                "analysis_method": "ai_enhanced_speaker_detection"
            }
            
        except Exception as e:
            logger.error(f"Error in speaker analysis: {e}")
            return self._basic_speaker_analysis(segments)
    
    def _basic_speaker_analysis(self, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform basic speaker analysis without AI."""
        try:
            # Simple heuristic: assume speaker changes at significant pauses or content shifts
            speaker_segments = []
            current_speaker = 1
            
            for i, segment in enumerate(segments):
                # Check for potential speaker change (gap > 2 seconds or content shift)
                if i > 0:
                    prev_segment = segments[i-1]
                    gap = segment['start_time'] - prev_segment['end_time']
                    
                    # Simple heuristic for speaker change
                    if gap > 2.0:  # Significant pause
                        current_speaker += 1
                
                speaker_segments.append({
                    "speaker_id": f"Speaker_{current_speaker}",
                    "start_time": segment['start_time'],
                    "end_time": segment['end_time'],
                    "text": segment['text'],
                    "confidence": segment.get('confidence', 0.0)
                })
            
            # Create speaker summary
            speakers = {}
            for seg in speaker_segments:
                speaker_id = seg['speaker_id']
                if speaker_id not in speakers:
                    speakers[speaker_id] = {
                        "speaker_id": speaker_id,
                        "total_duration": 0,
                        "segment_count": 0,
                        "avg_confidence": 0
                    }
                
                speakers[speaker_id]["total_duration"] += seg['end_time'] - seg['start_time']
                speakers[speaker_id]["segment_count"] += 1
                speakers[speaker_id]["avg_confidence"] += seg['confidence']
            
            # Calculate averages
            for speaker in speakers.values():
                if speaker["segment_count"] > 0:
                    speaker["avg_confidence"] /= speaker["segment_count"]
            
            return {
                "speakers": list(speakers.values()),
                "speaker_segments": speaker_segments,
                "speaker_count": len(speakers),
                "analysis_method": "basic_heuristic_detection"
            }
            
        except Exception as e:
            logger.error(f"Error in basic speaker analysis: {e}")
            return {
                "speakers": [],
                "speaker_segments": [],
                "speaker_count": 0
            }
    
    async def _create_timeline_correlation(self, keyframes: List[Dict[str, Any]], 
                                         ocr_results: List[Dict[str, Any]],
                                         audio_analysis: Dict[str, Any],
                                         duration: float) -> Dict[str, Any]:
        """Create timeline correlation between visual and audio content."""
        try:
            timeline_events = []
            
            # Add keyframe events
            for keyframe in keyframes:
                timeline_events.append({
                    "timestamp": keyframe['timestamp'],
                    "type": "visual_keyframe",
                    "content": {
                        "frame_number": keyframe['frame_number'],
                        "scene_change": keyframe.get('scene_change', False),
                        "histogram_diff": keyframe.get('histogram_diff', 0.0)
                    }
                })
            
            # Add OCR text events
            for ocr_result in ocr_results:
                if ocr_result.get('extracted_text', '').strip():
                    timeline_events.append({
                        "timestamp": ocr_result['timestamp'],
                        "type": "visual_text",
                        "content": {
                            "text": ocr_result['extracted_text'],
                            "confidence": ocr_result.get('confidence_score', 0.0),
                            "text_blocks": len(ocr_result.get('text_blocks', []))
                        }
                    })
            
            # Add audio transcription events
            audio_segments = audio_analysis.get('transcription', {}).get('segments', [])
            for segment in audio_segments:
                timeline_events.append({
                    "timestamp": segment['start_time'],
                    "type": "audio_speech",
                    "content": {
                        "text": segment['text'],
                        "duration": segment['end_time'] - segment['start_time'],
                        "confidence": segment.get('confidence', 0.0)
                    }
                })
            
            # Add speaker change events
            speaker_segments = audio_analysis.get('speaker_analysis', {}).get('speaker_segments', [])
            current_speaker = None
            for segment in speaker_segments:
                if segment['speaker_id'] != current_speaker:
                    timeline_events.append({
                        "timestamp": segment['start_time'],
                        "type": "speaker_change",
                        "content": {
                            "new_speaker": segment['speaker_id'],
                            "previous_speaker": current_speaker
                        }
                    })
                    current_speaker = segment['speaker_id']
            
            # Sort events by timestamp
            timeline_events.sort(key=lambda x: x['timestamp'])
            
            # Create correlation analysis
            correlations = await self._analyze_multimodal_correlations(timeline_events, duration)
            
            return {
                "timeline_events": timeline_events,
                "correlations": correlations,
                "total_events": len(timeline_events),
                "duration": duration,
                "events_per_minute": len(timeline_events) / (duration / 60) if duration > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error creating timeline correlation: {e}")
            return {
                "timeline_events": [],
                "correlations": {},
                "total_events": 0,
                "duration": duration,
                "error": str(e)
            }
    
    async def _analyze_multimodal_correlations(self, timeline_events: List[Dict[str, Any]], 
                                             duration: float) -> Dict[str, Any]:
        """Analyze correlations between visual and audio content."""
        try:
            correlations = {
                "visual_audio_sync": [],
                "content_themes": [],
                "presentation_flow": [],
                "engagement_points": []
            }
            
            # Find visual-audio synchronization points
            visual_events = [e for e in timeline_events if e['type'] in ['visual_keyframe', 'visual_text']]
            audio_events = [e for e in timeline_events if e['type'] in ['audio_speech', 'speaker_change']]
            
            # Look for correlations within 5-second windows
            correlation_window = 5.0
            
            for visual_event in visual_events:
                visual_time = visual_event['timestamp']
                
                # Find nearby audio events
                nearby_audio = [
                    audio for audio in audio_events
                    if abs(audio['timestamp'] - visual_time) <= correlation_window
                ]
                
                if nearby_audio:
                    correlation = {
                        "timestamp": visual_time,
                        "visual_event": visual_event,
                        "audio_events": nearby_audio,
                        "correlation_strength": len(nearby_audio) / 3.0  # Normalize
                    }
                    correlations["visual_audio_sync"].append(correlation)
            
            # Identify content themes by clustering similar events
            text_events = [e for e in timeline_events if 'text' in e.get('content', {})]
            if text_events:
                # Simple theme detection based on text content
                themes = self._extract_content_themes(text_events)
                correlations["content_themes"] = themes
            
            # Analyze presentation flow
            scene_changes = [e for e in timeline_events if e['type'] == 'visual_keyframe' 
                           and e.get('content', {}).get('scene_change', False)]
            speaker_changes = [e for e in timeline_events if e['type'] == 'speaker_change']
            
            correlations["presentation_flow"] = {
                "scene_changes": len(scene_changes),
                "speaker_changes": len(speaker_changes),
                "avg_scene_duration": duration / len(scene_changes) if scene_changes else duration,
                "presentation_style": self._classify_presentation_style(scene_changes, speaker_changes, duration)
            }
            
            return correlations
            
        except Exception as e:
            logger.error(f"Error analyzing multimodal correlations: {e}")
            return {}
    
    def _extract_content_themes(self, text_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract content themes from text events."""
        try:
            # Simple keyword-based theme extraction
            all_text = " ".join([
                event.get('content', {}).get('text', '') 
                for event in text_events
            ]).lower()
            
            # Define theme keywords
            theme_keywords = {
                "education": ["learn", "study", "education", "course", "lesson", "tutorial"],
                "technology": ["software", "computer", "programming", "code", "tech", "digital"],
                "business": ["business", "company", "market", "sales", "profit", "strategy"],
                "science": ["research", "experiment", "data", "analysis", "theory", "hypothesis"],
                "presentation": ["slide", "next", "previous", "agenda", "overview", "summary"]
            }
            
            themes = []
            for theme_name, keywords in theme_keywords.items():
                keyword_count = sum(all_text.count(keyword) for keyword in keywords)
                if keyword_count > 0:
                    themes.append({
                        "theme": theme_name,
                        "relevance_score": keyword_count / len(keywords),
                        "keyword_matches": keyword_count
                    })
            
            # Sort by relevance
            themes.sort(key=lambda x: x['relevance_score'], reverse=True)
            return themes[:5]  # Top 5 themes
            
        except Exception as e:
            logger.error(f"Error extracting content themes: {e}")
            return []
    
    def _classify_presentation_style(self, scene_changes: List[Dict], speaker_changes: List[Dict], 
                                   duration: float) -> str:
        """Classify the presentation style based on visual and audio patterns."""
        try:
            scene_rate = len(scene_changes) / (duration / 60) if duration > 0 else 0
            speaker_rate = len(speaker_changes) / (duration / 60) if duration > 0 else 0
            
            if scene_rate > 2 and speaker_rate < 0.5:
                return "slide_presentation"
            elif speaker_rate > 1:
                return "interview_discussion"
            elif scene_rate < 0.5 and speaker_rate < 0.5:
                return "lecture_monologue"
            elif scene_rate > 1 and speaker_rate > 0.5:
                return "interactive_tutorial"
            else:
                return "mixed_content"
                
        except:
            return "unknown"


# Global instance
video_agent = VideoAgent()