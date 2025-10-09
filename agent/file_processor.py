"""
File processing service for handling uploaded files and direct links.
Integrates with the specialized agent system for multi-modal content processing.
"""
import os
import asyncio
import base64
import json
import mimetypes
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import boto3
from strands import Agent
from bedrock_agentcore_starter_toolkit.operations.memory.manager import MemoryManager
from bedrock_agentcore_starter_toolkit.operations.memory.models.strategies import SemanticStrategy
from bedrock_agentcore.memory.session import MemorySessionManager
from bedrock_agentcore.memory.constants import ConversationalMessage, MessageRole
import requests
from urllib.parse import urlparse
import tempfile

# Import the specialized agents
from agents.agent_manager import agent_manager

# Import training service for assessment generation
try:
    from services.training_service import training_service
except ImportError:
    print("⚠️ Training service not available")
    training_service = None


class FileProcessor:
    """Processor for uploaded files and direct links."""
    
    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self.agent = Agent()
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=region)
        self.memory_manager = MemoryManager(region_name=region)
        self.memory = None
        self._memory_cache = {}  # Cache to reduce GetMemory calls
        self._session_cache = {}  # Cache memory sessions
        self._last_memory_check = 0  # Timestamp of last memory check
        
        # Use the specialized agent manager
        self.agent_manager = agent_manager
    
    def _init_memory(self):
        """Initialize or get existing memory for file knowledge bases with long-term strategies."""
        # Check cache first to reduce GetMemory calls
        cache_key = "MyTutorFileKnowledgeBase"
        current_time = time.time()
        
        # Use cached memory if available and recent (within 5 minutes)
        if (cache_key in self._memory_cache and 
            current_time - self._last_memory_check < 300):
            print("✅ Using cached memory to avoid quota limits")
            return self._memory_cache[cache_key]
        
        try:
            print("🔄 Initializing Enhanced AgentCore Memory for long-term learning...")
            memory = self.memory_manager.get_or_create_memory(
                name="MyTutorFileKnowledgeBase",
                description="Storage for processed file content",
                strategies=[
                    # Use the same strategy as existing memory to avoid conflicts
                    SemanticStrategy(
                        name="fileSemanticMemory",
                        namespaces=['/strategies/{memoryStrategyId}/actors/{actorId}/sessions/{sessionId}']
                    )
                ]
            )
            print(f"✅ Enhanced memory initialized: {memory.get('id')}")
            print(f"📚 Memory strategies: Content Semantic, Learning Episodic, Skill Procedural")
            
            # Cache the memory and update timestamp
            self._memory_cache[cache_key] = memory
            self._last_memory_check = current_time
            
            return memory
        except Exception as e:
            print(f"❌ Warning: Could not initialize enhanced memory: {e}")
            # Fallback to basic memory
            return self._init_basic_memory()
    
    def _init_basic_memory(self):
        """Fallback basic memory initialization."""
        try:
            memory = self.memory_manager.get_or_create_memory(
                name="MyTutorFileKnowledgeBase",
                description="Storage for processed file content",
                strategies=[
                    SemanticStrategy(
                        name="fileSemanticMemory",
                        namespaces=['/strategies/{memoryStrategyId}/actors/{actorId}/sessions/{sessionId}']
                    )
                ]
            )
            return memory
        except Exception as e:
            print(f"❌ Could not initialize basic memory: {e}")
            return None
    
    def _chunk_content_contextually(self, content: str, metadata: Dict[str, Any], max_size: int = 8000) -> List[str]:
        """Split content into contextual chunks that preserve semantic meaning."""
        try:
            metadata_json = json.dumps(metadata, indent=2)
            
            # Calculate header size for each chunk
            header_template = f"""
File: {metadata.get('filename', 'Unknown')} (Chunk {{chunk_num}} of {{total_chunks}})
Type: {metadata.get('content_type', 'Unknown')}
Size: {metadata.get('file_size', 0)} bytes
Processed: {metadata.get('processed_at', datetime.now().isoformat())}

Content:
"""
            footer_template = f"""

Metadata:
{metadata_json}
"""
            
            # Calculate available space for content per chunk
            header_size = len(header_template.format(chunk_num=99, total_chunks=99))
            footer_size = len(footer_template)
            max_content_size = max_size - header_size - footer_size - 200  # Extra buffer for overlap
            
            # If content fits in one chunk, return as-is
            if len(content) <= max_content_size:
                full_content = f"""
File: {metadata.get('filename', 'Unknown')}
Type: {metadata.get('content_type', 'Unknown')}
Size: {metadata.get('file_size', 0)} bytes
Processed: {metadata.get('processed_at', datetime.now().isoformat())}

Content:
{content}

Metadata:
{metadata_json}
"""
                return [full_content]
            
            # Contextual chunking with overlap for better semantic search
            chunks = []
            content_chunks = self._split_content_contextually(content, max_content_size)
            total_chunks = len(content_chunks)
            
            print(f"📄 Creating {total_chunks} contextual chunks with semantic overlap to preserve meaning")
            
            for i, chunk_data in enumerate(content_chunks, 1):
                chunk_content = chunk_data['content']
                chunk_context = chunk_data.get('context', '')
                
                # Add context from previous/next chunks for better semantic understanding
                if chunk_context:
                    chunk_with_context = f"{chunk_context}\n\n--- Main Content ---\n{chunk_content}"
                else:
                    chunk_with_context = chunk_content
                
                chunk = f"""
File: {metadata.get('filename', 'Unknown')} (Chunk {i} of {total_chunks})
Type: {metadata.get('content_type', 'Unknown')}
Size: {metadata.get('file_size', 0)} bytes
Processed: {metadata.get('processed_at', datetime.now().isoformat())}

Content:
{chunk_with_context}

Metadata:
{metadata_json}
"""
                chunks.append(chunk)
            
            return chunks
            
        except Exception as e:
            print(f"Error in contextual chunking: {e}")
            return [f"File: {metadata.get('filename', 'Unknown')}\nType: {metadata.get('content_type', 'Unknown')}\n[Content processing error]"]
    
    def _split_content_contextually(self, content: str, max_chunk_size: int) -> List[Dict[str, str]]:
        """Split content into contextual chunks with semantic boundaries."""
        try:
            # Try to split on natural boundaries (paragraphs, sections, sentences)
            chunks = []
            
            # First, try splitting on double newlines (paragraphs)
            paragraphs = content.split('\n\n')
            
            current_chunk = ""
            current_size = 0
            overlap_size = 200  # Characters to overlap between chunks for context
            
            for i, paragraph in enumerate(paragraphs):
                paragraph_size = len(paragraph)
                
                # If adding this paragraph would exceed the limit
                if current_size + paragraph_size > max_chunk_size and current_chunk:
                    # Save current chunk with context
                    context = ""
                    if chunks:  # Add context from previous chunk
                        prev_chunk = chunks[-1]['content']
                        context = f"[Previous context: ...{prev_chunk[-overlap_size:]}]"
                    
                    chunks.append({
                        'content': current_chunk.strip(),
                        'context': context
                    })
                    
                    # Start new chunk with overlap from previous chunk
                    if len(current_chunk) > overlap_size:
                        current_chunk = f"[Continued from previous chunk: ...{current_chunk[-overlap_size:]}]\n\n{paragraph}"
                        current_size = len(current_chunk)
                    else:
                        current_chunk = paragraph
                        current_size = paragraph_size
                else:
                    # Add paragraph to current chunk
                    if current_chunk:
                        current_chunk += f"\n\n{paragraph}"
                        current_size += paragraph_size + 2  # +2 for \n\n
                    else:
                        current_chunk = paragraph
                        current_size = paragraph_size
            
            # Add the last chunk
            if current_chunk.strip():
                context = ""
                if chunks:  # Add context from previous chunk
                    prev_chunk = chunks[-1]['content']
                    context = f"[Previous context: ...{prev_chunk[-overlap_size:]}]"
                
                chunks.append({
                    'content': current_chunk.strip(),
                    'context': context
                })
            
            # If we still have chunks that are too large, split them further
            final_chunks = []
            for chunk in chunks:
                if len(chunk['content']) > max_chunk_size:
                    # Split large chunks on sentence boundaries
                    sentences = chunk['content'].split('. ')
                    sub_chunk = ""
                    
                    for sentence in sentences:
                        if len(sub_chunk + sentence) > max_chunk_size and sub_chunk:
                            final_chunks.append({
                                'content': sub_chunk.strip(),
                                'context': chunk['context']
                            })
                            sub_chunk = sentence + '. '
                        else:
                            sub_chunk += sentence + '. '
                    
                    if sub_chunk.strip():
                        final_chunks.append({
                            'content': sub_chunk.strip(),
                            'context': chunk['context']
                        })
                else:
                    final_chunks.append(chunk)
            
            return final_chunks if final_chunks else [{'content': content[:max_chunk_size], 'context': ''}]
            
        except Exception as e:
            print(f"Error in contextual splitting: {e}")
            # Fallback to simple chunking
            simple_chunks = [content[i:i + max_chunk_size] for i in range(0, len(content), max_chunk_size)]
            return [{'content': chunk, 'context': ''} for chunk in simple_chunks]
    
    def _clean_session_id(self, session_id: str) -> str:
        """Clean session ID to match AWS pattern: [a-zA-Z0-9][a-zA-Z0-9-_]*"""
        # Remove invalid characters, keep only alphanumeric, hyphens, and underscores
        cleaned = ''.join(c for c in session_id if c.isalnum() or c in '-_')
        # Ensure it starts with alphanumeric
        if cleaned and not cleaned[0].isalnum():
            cleaned = 'a' + cleaned
        # Limit length
        return cleaned[:50] if cleaned else "defaultSession"
    
    def _extract_key_concepts(self, content: str) -> List[str]:
        """Extract key educational concepts from content."""
        if not content:
            return []
        
        # Simple keyword extraction (could be enhanced with NLP)
        import re
        
        # Common educational/programming concepts
        concepts = []
        content_lower = content.lower()
        
        # Programming concepts
        prog_concepts = ['function', 'variable', 'loop', 'array', 'object', 'class', 'method', 
                        'algorithm', 'data structure', 'recursion', 'inheritance', 'polymorphism']
        
        # General educational concepts  
        edu_concepts = ['definition', 'example', 'theory', 'practice', 'concept', 'principle',
                       'formula', 'equation', 'process', 'procedure', 'step', 'method']
        
        for concept in prog_concepts + edu_concepts:
            if concept in content_lower:
                concepts.append(concept.title())
        
        return concepts[:5]  # Limit to top 5 concepts
    
    def _analyze_content_structure(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the structure of the content for educational purposes."""
        content_type = metadata.get('content_type', '')
        
        structure = {
            "format": "unknown",
            "interactive": False,
            "has_examples": False,
            "has_exercises": False,
            "multimedia": False
        }
        
        if 'video' in content_type:
            structure.update({
                "format": "video",
                "multimedia": True,
                "interactive": True,
                "estimated_engagement": "high"
            })
        elif 'pdf' in content_type or 'document' in content_type:
            structure.update({
                "format": "document", 
                "multimedia": False,
                "interactive": False,
                "estimated_engagement": "medium"
            })
        elif 'audio' in content_type:
            structure.update({
                "format": "audio",
                "multimedia": True,
                "interactive": False,
                "estimated_engagement": "medium"
            })
        
        return structure
    
    async def _rate_limited_operation(self, operation_func, *args, **kwargs):
        """Execute memory operations with rate limiting to avoid quota issues."""
        max_retries = 3
        base_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                return await operation_func(*args, **kwargs) if asyncio.iscoroutinefunction(operation_func) else operation_func(*args, **kwargs)
            except Exception as e:
                if "ThrottlingException" in str(e) or "Too many requests" in str(e):
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)  # Exponential backoff
                        print(f"⏳ Rate limited, waiting {delay}s before retry {attempt + 1}/{max_retries}")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        print(f"❌ Max retries reached for memory operation: {e}")
                        return None
                else:
                    raise e
        return None
    
    def _save_to_memory(self, user_id: str, content_id: str, content: str, metadata: Dict[str, Any]):
        """Save processed content to enhanced long-term memory with contextual organization."""
        if self.memory is None:
            self.memory = self._init_memory()
        
        if not self.memory:
            return
        
        try:
            session_manager = MemorySessionManager(
                memory_id=self.memory.get("id"),
                region_name=self.region
            )
            
            # Clean the session ID to ensure it matches AWS requirements
            clean_content_id = self._clean_session_id(content_id)
            
            # Determine content type and create appropriate session
            content_type = metadata.get('content_type', 'unknown')
            file_category = metadata.get('category', 'general')
            
            # Create contextual session based on content type
            if 'video' in content_type:
                session_context = f"video_content_{clean_content_id}"
            elif 'pdf' in content_type or 'document' in content_type:
                session_context = f"document_content_{clean_content_id}"
            elif 'audio' in content_type:
                session_context = f"audio_content_{clean_content_id}"
            else:
                session_context = f"general_content_{clean_content_id}"
            
            # Check session cache first
            session_cache_key = f"{user_id}_{session_context}"
            if session_cache_key in self._session_cache:
                session = self._session_cache[session_cache_key]
                print("✅ Using cached session to avoid quota limits")
            else:
                session = session_manager.create_memory_session(
                    actor_id=user_id,
                    session_id=session_context
                )
                # Cache the session for reuse
                self._session_cache[session_cache_key] = session
            
            # Store content with contextual chunking to preserve all information
            content_chunks = self._chunk_content_contextually(content, metadata)
            
            # Store each chunk as a separate message for complete preservation
            for i, chunk in enumerate(content_chunks):
                session.add_turns(
                    messages=[
                        ConversationalMessage(
                            chunk,
                            MessageRole.ASSISTANT
                        )
                    ]
                )
            
            if len(content_chunks) > 1:
                print(f"✅ Saved file content in {len(content_chunks)} contextual chunks: {metadata.get('filename')}")
            else:
                print(f"✅ Saved file content to memory: {metadata.get('filename')}")
            print(f"✅ Saved file content to memory: {metadata.get('filename')}")
            
        except Exception as e:
            print(f"Warning: Could not save file to memory: {e}")
    
    async def process_files_with_agents(self, file_paths: List[str], user_id: str) -> Dict[str, Any]:
        """Process files using specialized agents."""
        try:
            print(f"🤖 Processing {len(file_paths)} files with specialized agents")

            # Use the agent manager to process files
            results = await self.agent_manager.process_files_batch(file_paths, user_id)

            # Check for errors in any agent results
            errors = []
            success_count = 0
            for agent_type, agent_results in results.items():
                for result in agent_results:
                    if result.get('status') == 'error':
                        error_msg = result.get('error', 'Unknown error')
                        errors.append(f"{agent_type}: {error_msg}")
                        print(f"❌ {agent_type} agent error: {error_msg}")
                    elif result.get('status') == 'completed':
                        success_count += 1
                        await self._save_agent_result_to_memory(user_id, result)

            # If there are errors, return error status with detailed message
            if errors:
                error_message = "; ".join(errors)
                return {
                    "status": "error",
                    "message": error_message,
                    "results": results,
                    "success_count": success_count,
                    "error_count": len(errors)
                }

            return {
                "status": "completed",
                "message": f"Processed {len(file_paths)} files with specialized agents",
                "results": results,
                "agent_stats": self.agent_manager.get_processing_stats()
            }

        except Exception as e:
            print(f"❌ Error processing files with agents: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def _save_agent_result_to_memory(self, user_id: str, result: Dict[str, Any]):
        """Save agent processing result to memory."""
        try:
            if self.memory is None:
                self.memory = self._init_memory()
            
            if not self.memory:
                return
            
            session_manager = MemorySessionManager(
                memory_id=self.memory.get("id"),
                region_name=self.region
            )
            
            # Create unique session ID for this file
            file_path = result.get('file_path', 'unknown')
            content_id = f"agent_{result.get('agent_type')}_{os.path.basename(file_path)}"
            
            # Clean the session ID to ensure it matches AWS requirements
            clean_content_id = self._clean_session_id(content_id)
            
            session = session_manager.create_memory_session(
                actor_id=user_id,
                session_id=clean_content_id
            )
            
            # Format content for memory storage
            memory_content = f"""
Agent Type: {result.get('agent_type', 'unknown').upper()}
File: {os.path.basename(file_path)}
Status: {result.get('status')}
Processed: {datetime.now().isoformat()}

Content Analysis:
{json.dumps(result.get('content', {}), indent=2)}

AI Analysis:
{result.get('analysis', {}).get('ai_analysis', 'No analysis available')}

Metadata:
{json.dumps(result.get('metadata', {}), indent=2)}
"""

            # Use contextual chunking to avoid 9000 char limit
            content_chunks = self._chunk_content_contextually(memory_content, result.get('metadata', {}))

            for chunk in content_chunks:
                session.add_turns(
                    messages=[
                        ConversationalMessage(
                            chunk,
                            MessageRole.ASSISTANT
                        )
                    ]
                )

            if len(content_chunks) > 1:
                print(f"✅ Saved {result.get('agent_type')} agent result in {len(content_chunks)} chunks: {os.path.basename(file_path)}")
            else:
                print(f"✅ Saved {result.get('agent_type')} agent result to memory: {os.path.basename(file_path)}")
            
            print(f"✅ Saved {result.get('agent_type')} agent result to memory: {os.path.basename(file_path)}")
            
        except Exception as e:
            print(f"⚠️ Could not save agent result to memory: {e}")
    
    async def generate_training_content(self, kb_id: str, agent_results: Dict[str, Any],
                                      training_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate training content from processed agent results."""
        try:
            if not training_service:
                return {
                    "status": "error",
                    "message": "Training service not available",
                    "training_content": None
                }
            
            print(f"🎓 Generating training content for KB: {kb_id}")
            
            # Use training service to generate content
            result = await training_service.generate_training_content_from_kb(
                kb_id, agent_results, training_config
            )
            
            return result
            
        except Exception as e:
            print(f"❌ Training content generation failed: {e}")
            return {
                "status": "error",
                "message": f"Training generation failed: {str(e)}",
                "training_content": None
            }
    
    def _resolve_file_path(self, file_path: Path) -> Path:
        """Resolve file path relative to project structure."""
        print(f"🔍 Resolving file path: {file_path}")
        print(f"🔍 Current working directory: {Path.cwd()}")
        
        # If the path exists as-is, use it
        if file_path.exists():
            print(f"✅ Found file at original path: {file_path}")
            return file_path
        
        # Try in backend directory (most common case)
        backend_path = Path("backend") / file_path
        print(f"🔍 Trying backend path: {backend_path}")
        if backend_path.exists():
            print(f"✅ Found file at backend path: {backend_path}")
            return backend_path
        
        # Try relative to backend directory (from agent directory)
        backend_relative_path = Path("../backend") / file_path
        print(f"🔍 Trying backend relative path: {backend_relative_path}")
        if backend_relative_path.exists():
            print(f"✅ Found file at backend relative path: {backend_relative_path}")
            return backend_relative_path
        
        # Try absolute path from project root
        project_root_path = Path("..") / file_path
        print(f"🔍 Trying project root path: {project_root_path}")
        if project_root_path.exists():
            print(f"✅ Found file at project root path: {project_root_path}")
            return project_root_path
        
        # Return original path if nothing works
        print(f"❌ Could not resolve file path, using original: {file_path}")
        return file_path
    
    async def process_pdf(self, file_path: Path) -> Dict[str, Any]:
        """Extract text and images from PDF."""
        try:
            resolved_path = self._resolve_file_path(file_path)
            print(f"📄 Processing PDF file: {resolved_path}")
            text_content = ""
            images = []
            
            with open(resolved_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extract text from all pages
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_content += f"\n--- Page {page_num + 1} ---\n{page_text}"
                
                # Note: Image extraction from PDF would require additional libraries
                # like pdf2image or pymupdf for more advanced processing
            
            return {
                "text_content": text_content,
                "images": images,
                "page_count": len(pdf_reader.pages),
                "metadata": {
                    "type": "pdf",
                    "pages": len(pdf_reader.pages)
                }
            }
            
        except Exception as e:
            return {
                "text_content": f"Error processing PDF: {str(e)}",
                "images": [],
                "page_count": 0,
                "metadata": {"type": "pdf", "error": str(e)}
            }
    
    async def process_docx(self, file_path: Path) -> Dict[str, Any]:
        """Extract text from Word document."""
        try:
            resolved_path = self._resolve_file_path(file_path)
            print(f"📝 Processing DOCX file: {resolved_path}")
            doc = docx.Document(resolved_path)
            text_content = ""
            
            for paragraph in doc.paragraphs:
                text_content += paragraph.text + "\n"
            
            # Extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        text_content += cell.text + "\t"
                    text_content += "\n"
            
            return {
                "text_content": text_content,
                "paragraph_count": len(doc.paragraphs),
                "table_count": len(doc.tables),
                "metadata": {
                    "type": "docx",
                    "paragraphs": len(doc.paragraphs),
                    "tables": len(doc.tables)
                }
            }
            
        except Exception as e:
            return {
                "text_content": f"Error processing DOCX: {str(e)}",
                "paragraph_count": 0,
                "table_count": 0,
                "metadata": {"type": "docx", "error": str(e)}
            }
    
    async def process_pptx(self, file_path: Path) -> Dict[str, Any]:
        """Extract text from PowerPoint presentation."""
        try:
            resolved_path = self._resolve_file_path(file_path)
            print(f"📊 Processing PPTX file: {resolved_path}")
            prs = Presentation(resolved_path)
            text_content = ""
            slide_count = 0
            
            for slide_num, slide in enumerate(prs.slides):
                slide_count += 1
                text_content += f"\n--- Slide {slide_num + 1} ---\n"
                
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text_content += shape.text + "\n"
            
            return {
                "text_content": text_content,
                "slide_count": slide_count,
                "metadata": {
                    "type": "pptx",
                    "slides": slide_count
                }
            }
            
        except Exception as e:
            return {
                "text_content": f"Error processing PPTX: {str(e)}",
                "slide_count": 0,
                "metadata": {"type": "pptx", "error": str(e)}
            }
    
    async def process_image(self, file_path: Path) -> Dict[str, Any]:
        """Process image file and extract visual information."""
        try:
            resolved_path = self._resolve_file_path(file_path)
            print(f"🖼️ Processing image file: {resolved_path}")
            # Open and analyze image
            with Image.open(resolved_path) as img:
                width, height = img.size
                format_type = img.format
                mode = img.mode
                
                # Convert to base64 for AI analysis
                import io
                buffer = io.BytesIO()
                img.save(buffer, format=format_type or 'PNG')
                img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                # Use AI to describe the image
                description = await self._analyze_image_with_ai(img_base64)
                
                return {
                    "description": description,
                    "image_base64": img_base64,
                    "metadata": {
                        "type": "image",
                        "width": width,
                        "height": height,
                        "format": format_type,
                        "mode": mode
                    }
                }
                
        except Exception as e:
            return {
                "description": f"Error processing image: {str(e)}",
                "image_base64": "",
                "metadata": {"type": "image", "error": str(e)}
            }
    
    async def process_audio(self, file_path: Path) -> Dict[str, Any]:
        """Process audio file and extract transcript."""
        try:
            resolved_path = self._resolve_file_path(file_path)
            print(f"🎵 Processing audio file: {resolved_path}")
            # Convert audio to WAV if needed
            audio_file = resolved_path
            
            # Use speech recognition to transcribe
            with sr.AudioFile(str(audio_file)) as source:
                audio = self.recognizer.record(source)
                
            try:
                transcript = self.recognizer.recognize_google(audio)
            except sr.UnknownValueError:
                transcript = "Could not understand audio"
            except sr.RequestError as e:
                transcript = f"Speech recognition error: {e}"
            
            return {
                "transcript": transcript,
                "metadata": {
                    "type": "audio",
                    "duration": "unknown"  # Would need additional library for duration
                }
            }
            
        except Exception as e:
            return {
                "transcript": f"Error processing audio: {str(e)}",
                "metadata": {"type": "audio", "error": str(e)}
            }
    
    async def process_video(self, file_path: Path) -> Dict[str, Any]:
        """Process video file and extract frames/audio."""
        try:
            resolved_path = self._resolve_file_path(file_path)
            print(f"🎬 Processing video file: {resolved_path}")
            
            # Use OpenCV to extract video information
            cap = cv2.VideoCapture(str(resolved_path))
            
            if not cap.isOpened():
                raise Exception("Could not open video file")
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Extract a few key frames
            key_frames = []
            frame_indices = [0, frame_count // 4, frame_count // 2, 3 * frame_count // 4, frame_count - 1]
            
            for frame_idx in frame_indices:
                if frame_idx < frame_count:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                    ret, frame = cap.read()
                    if ret:
                        # Convert frame to base64
                        _, buffer = cv2.imencode('.jpg', frame)
                        frame_base64 = base64.b64encode(buffer).decode('utf-8')
                        key_frames.append(frame_base64)
            
            cap.release()
            
            # Analyze key frames with AI
            frame_descriptions = []
            for i, frame_b64 in enumerate(key_frames[:3]):  # Limit to 3 frames
                description = await self._analyze_image_with_ai(frame_b64)
                frame_descriptions.append(f"Frame {i+1}: {description}")
            
            return {
                "frame_descriptions": frame_descriptions,
                "key_frames": key_frames,
                "metadata": {
                    "type": "video",
                    "duration": duration,
                    "fps": fps,
                    "frame_count": frame_count,
                    "width": width,
                    "height": height
                }
            }
            
        except Exception as e:
            return {
                "frame_descriptions": [f"Error processing video: {str(e)}"],
                "key_frames": [],
                "metadata": {"type": "video", "error": str(e)}
            }
    
    async def _analyze_image_with_ai(self, image_base64: str) -> str:
        """Analyze image using Bedrock AI."""
        try:
            prompt = """
Analyze this image and provide a detailed description focusing on:
1. Main subject matter and content
2. Text visible in the image (if any)
3. Educational or informational content
4. Key visual elements
5. Context and purpose

Provide a clear, concise description suitable for educational content analysis.
"""
            
            response = self.bedrock_client.invoke_model(
                modelId=os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-sonnet-20241022-v2:0"),
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt
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
            return result['content'][0]['text']
            
        except Exception as e:
            return f"Could not analyze image: {str(e)}"
    
    async def download_and_process_link(self, url: str) -> Dict[str, Any]:
        """Download content from a direct link and process it."""
        try:
            # Parse URL to determine expected content type
            parsed_url = urlparse(url)
            file_extension = Path(parsed_url.path).suffix.lower()
            
            # Download the file
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
                temp_file.write(response.content)
                temp_path = Path(temp_file.name)
            
            try:
                # Process based on file type
                if file_extension == '.pdf':
                    result = await self.process_pdf(temp_path)
                elif file_extension in ['.docx', '.doc']:
                    result = await self.process_docx(temp_path)
                elif file_extension in ['.pptx', '.ppt']:
                    result = await self.process_pptx(temp_path)
                elif file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    result = await self.process_image(temp_path)
                elif file_extension in ['.mp3', '.wav', '.m4a']:
                    result = await self.process_audio(temp_path)
                elif file_extension in ['.mp4', '.avi', '.mov']:
                    result = await self.process_video(temp_path)
                else:
                    # Try to process as text
                    with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    result = {
                        "text_content": content,
                        "metadata": {"type": "text", "source": "direct_link"}
                    }
                
                result["source_url"] = url
                return result
                
            finally:
                # Clean up temporary file
                temp_path.unlink(missing_ok=True)
                
        except Exception as e:
            return {
                "text_content": f"Error downloading/processing link {url}: {str(e)}",
                "metadata": {"type": "error", "source": "direct_link", "url": url}
            }
    
    async def process_uploaded_files(
        self, 
        file_paths: List[str], 
        user_id: str,
        processing_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process multiple uploaded files."""
        try:
            processed_files = []
            total_files = len(file_paths)
            
            for i, file_path_str in enumerate(file_paths):
                file_path = Path(file_path_str)
                
                if not file_path.exists():
                    processed_files.append({
                        "filename": file_path.name,
                        "status": "error",
                        "error": "File not found"
                    })
                    continue
                
                # Determine file type
                mime_type, _ = mimetypes.guess_type(file_path)
                file_extension = file_path.suffix.lower()
                
                # Process based on file type
                if file_extension == '.pdf':
                    result = await self.process_pdf(file_path)
                elif file_extension in ['.docx', '.doc']:
                    result = await self.process_docx(file_path)
                elif file_extension in ['.pptx', '.ppt']:
                    result = await self.process_pptx(file_path)
                elif file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    result = await self.process_image(file_path)
                elif file_extension in ['.mp3', '.wav', '.m4a']:
                    result = await self.process_audio(file_path)
                elif file_extension in ['.mp4', '.avi', '.mov']:
                    result = await self.process_video(file_path)
                else:
                    result = {
                        "text_content": f"Unsupported file type: {file_extension}",
                        "metadata": {"type": "unsupported"}
                    }
                
                # Add file metadata
                result["filename"] = file_path.name
                result["file_size"] = file_path.stat().st_size
                result["content_type"] = mime_type
                result["processed_at"] = datetime.now().isoformat()
                
                # Save to memory
                content_id = f"file_{abs(hash(file_path_str)) % 10000000}"
                content = result.get("text_content", "") or result.get("description", "") or result.get("transcript", "")
                
                if content:
                    self._save_to_memory(user_id, content_id, content, result)
                
                processed_files.append({
                    "filename": file_path.name,
                    "status": "completed",
                    "content": result
                })
            
            return {
                "status": "completed",
                "total_files": total_files,
                "processed_files": processed_files,
                "message": f"Processed {len(processed_files)} files"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"File processing failed: {str(e)}"
            }
    
    async def process_direct_links(
        self,
        links: List[str],
        user_id: str,
        processing_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process multiple direct links."""
        try:
            processed_links = []
            total_links = len(links)
            
            for i, url in enumerate(links):
                result = await self.download_and_process_link(url)
                
                # Save to memory
                content_id = f"link_{abs(hash(url)) % 10000000}"
                content = result.get("text_content", "") or result.get("description", "") or result.get("transcript", "")
                
                if content:
                    result["processed_at"] = datetime.now().isoformat()
                    self._save_to_memory(user_id, content_id, content, result)
                
                processed_links.append({
                    "url": url,
                    "status": "completed" if "error" not in result.get("metadata", {}) else "error",
                    "content": result
                })
            
            return {
                "status": "completed",
                "total_links": total_links,
                "processed_links": processed_links,
                "message": f"Processed {len(processed_links)} links"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Link processing failed: {str(e)}"
            }


# Global processor instance
file_processor = FileProcessor()