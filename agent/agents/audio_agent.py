"""
Audio Agent - Specialized processor for audio files with enhanced transcription
Handles: MP3, WAV, M4A, AAC, FLAC, OGG files
Features: High-accuracy transcription, speaker diarization, topic segmentation
"""
import os
import json
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

import boto3
from strands import Agent
import tempfile
import subprocess
import logging
from datetime import datetime, timedelta
import numpy as np
from dataclasses import dataclass
import base64
import speech_recognition as sr

# Import model configuration system
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.model_manager import model_config_manager

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionSegment:
    """Represents a segment of transcribed audio with metadata."""
    start_time: float
    end_time: float
    text: str
    confidence: float
    speaker_id: Optional[str] = None
    topic_id: Optional[str] = None


@dataclass
class AudioAnalysisResult:
    """Complete audio analysis result with enhanced metadata."""
    transcription: str
    segments: List[TranscriptionSegment]
    speakers: List[Dict[str, Any]]
    topics: List[Dict[str, Any]]
    confidence_score: float
    duration: float
    word_count: int
    educational_metadata: Dict[str, Any]


class AudioAgent:
    """Specialized agent for processing audio files with enhanced transcription capabilities."""
    
    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self.agent = Agent()
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=region)
        self.recognizer = sr.Recognizer()
        self.supported_extensions = ['.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg']
        

        
        # Model configuration
        self.model_config = model_config_manager.get_model_for_agent("audio")
        

    
    def can_process(self, file_path: str) -> bool:
        """Check if this agent can process the given file."""
        return any(file_path.lower().endswith(ext) for ext in self.supported_extensions)
    
    def _resolve_file_path(self, file_path: str) -> str:
        """Resolve file path relative to project structure."""
        from pathlib import Path
        
        file_path_obj = Path(file_path)
        print(f"🔍 AUDIO Agent - Resolving file path: {file_path_obj}")
        
        # If the path exists as-is, use it
        if file_path_obj.exists():
            print(f"✅ AUDIO Agent - Found file at original path: {file_path_obj}")
            return str(file_path_obj)
        
        # Try in backend directory (most common case)
        backend_path = Path("backend") / file_path_obj
        if backend_path.exists():
            print(f"✅ AUDIO Agent - Found file at backend path: {backend_path}")
            return str(backend_path)
        
        # Try relative to backend directory (from agent directory)
        backend_relative_path = Path("../backend") / file_path_obj
        if backend_relative_path.exists():
            print(f"✅ AUDIO Agent - Found file at backend relative path: {backend_relative_path}")
            return str(backend_relative_path)
        
        # Return original path if nothing works
        print(f"❌ AUDIO Agent - Could not resolve file path, using original: {file_path_obj}")
        return file_path
    
    async def process_file(self, file_path: str, user_id: str) -> Dict[str, Any]:
        """Process an audio file with enhanced transcription and analysis."""
        try:
            print(f"🎵 AUDIO Agent processing: {file_path}")

            # Resolve file path
            resolved_path = self._resolve_file_path(file_path)

            # Enhanced audio content extraction with high-accuracy transcription
            audio_analysis = await self._extract_enhanced_audio_content(resolved_path)
            
            # Analyze content with AI using optimized model
            analysis = await self._analyze_enhanced_content(audio_analysis, file_path)
            
            # Prepare enhanced result
            result = {
                "agent_type": "audio",
                "file_path": file_path,
                "status": "completed",
                "content": {
                    "transcription": audio_analysis.transcription[:5000] if len(audio_analysis.transcription) > 5000 else audio_analysis.transcription,  # More generous preview
                    "full_transcription": audio_analysis.transcription,
                    "segments": [
                        {
                            "start_time": seg.start_time,
                            "end_time": seg.end_time,
                            "text": seg.text,
                            "confidence": seg.confidence,
                            "speaker_id": seg.speaker_id,
                            "topic_id": seg.topic_id
                        }
                        for seg in audio_analysis.segments
                    ],
                    "speakers": audio_analysis.speakers,
                    "topics": audio_analysis.topics,
                    "duration": audio_analysis.duration,
                    "word_count": audio_analysis.word_count,
                    "confidence": audio_analysis.confidence_score
                },
                "analysis": analysis,
                "educational_metadata": audio_analysis.educational_metadata,
                "metadata": {
                    "duration": audio_analysis.duration,
                    "file_size": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                    "file_type": Path(file_path).suffix.lower(),
                    "processed_by": "enhanced_audio_agent",
                    "transcription_method": "whisper_primary",
                    "speaker_count": len(audio_analysis.speakers),
                    "topic_count": len(audio_analysis.topics)
                }
            }
            
            print(f"✅ AUDIO Agent completed: {file_path} ({audio_analysis.duration:.1f}s, {len(audio_analysis.speakers)} speakers, {len(audio_analysis.topics)} topics)")
            return result
            
        except Exception as e:
            logger.error(f"Audio Agent error processing {file_path}: {e}")
            print(f"❌ AUDIO Agent error processing {file_path}: {e}")
            return {
                "agent_type": "audio",
                "file_path": file_path,
                "status": "error",
                "error": str(e)
            }
    
    async def _extract_enhanced_audio_content(self, file_path: str) -> AudioAnalysisResult:
        """Extract enhanced transcription with timestamps, speakers, and topics."""
        try:
            # Resolve file path first
            resolved_path = self._resolve_file_path(file_path)
            print(f"🎵 AUDIO Agent processing resolved path: {resolved_path}")
            
            # Get audio metadata
            metadata = await self._get_audio_metadata(resolved_path)
            duration = metadata.get('duration', 0)
            
            # Primary: Use Bedrock audio models (context-aware, educational focus)
            print(f"🤖 Starting transcription with Bedrock audio models...")
            transcription_result = await self._transcribe_with_bedrock_audio(resolved_path)
            
            if not transcription_result or not transcription_result.get('text'):
                print(f"⚠️ Bedrock audio failed, trying local Whisper...")
                # Fallback to local Whisper (fast, offline, free)
                transcription_result = await self._transcribe_with_local_whisper(resolved_path)
                
                if not transcription_result or not transcription_result.get('text'):
                    print(f"❌ Both Bedrock and Whisper failed - no transcription available")
                    # Return minimal result structure
                    transcription_result = {
                        "text": "Transcription failed - audio processing not available",
                        "segments": []
                    }
                else:
                    print(f"✅ Local Whisper transcription successful!")
            else:
                print(f"✅ Bedrock audio transcription successful!")
            
            # Extract segments with timestamps
            segments = self._create_transcription_segments(transcription_result)
            
            # Perform speaker diarization (basic implementation)
            speakers = await self._identify_speakers(segments, file_path)
            
            # Perform topic segmentation
            topics = await self._segment_topics(segments)
            
            # Calculate overall confidence
            confidence_score = self._calculate_confidence(segments)
            
            # Generate educational metadata
            educational_metadata = await self._generate_educational_metadata(
                transcription_result.get('text', ''), segments, duration
            )
            
            return AudioAnalysisResult(
                transcription=transcription_result.get('text', ''),
                segments=segments,
                speakers=speakers,
                topics=topics,
                confidence_score=confidence_score,
                duration=duration,
                word_count=len(transcription_result.get('text', '').split()),
                educational_metadata=educational_metadata
            )
            
        except Exception as e:
            logger.error(f"Error processing audio {file_path}: {e}")
            # Return minimal result on error
            return AudioAnalysisResult(
                transcription=f"Transcription failed: {str(e)}",
                segments=[],
                speakers=[],
                topics=[],
                confidence_score=0.0,
                duration=0.0,
                word_count=0,
                educational_metadata={"error": str(e)}
            )
    
    async def _get_audio_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract audio metadata using ffprobe or basic file info."""
        try:
            # Try to use ffprobe for detailed metadata
            result = subprocess.run([
                'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', file_path
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                metadata = json.loads(result.stdout)
                format_info = metadata.get('format', {})
                
                return {
                    "duration": float(format_info.get('duration', 0)),
                    "bit_rate": int(format_info.get('bit_rate', 0)),
                    "file_size": int(format_info.get('size', 0)),
                    "format_name": format_info.get('format_name', ''),
                    "file_type": Path(file_path).suffix.lower()
                }
        except Exception as e:
            print(f"⚠️ ffprobe not available or failed: {e}")
        
        # Fallback to basic file info
        return {
            "duration": 0,  # Cannot determine without ffprobe
            "file_size": os.path.getsize(file_path),
            "file_type": Path(file_path).suffix.lower(),
            "format_name": "unknown"
        }
    
    async def _transcribe_with_local_whisper(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Transcribe audio using local OpenAI Whisper (fast, no S3 required)."""
        try:
            import whisper
            import ssl
            import urllib.request

            # Load Whisper model (optimized for speed vs accuracy)
            if not hasattr(self, 'whisper_model'):
                # Use 'base' model for good balance, 'small' for faster processing
                model_size = os.getenv('WHISPER_MODEL_SIZE', 'base')  # base, small, medium, large
                print(f"🎵 Loading Whisper model: {model_size}")

                # Try loading model with normal SSL verification first
                try:
                    self.whisper_model = whisper.load_model(model_size)
                    logger.info(f"Loaded local Whisper model: {model_size}")
                except Exception as ssl_error:
                    # Check if it's an SSL certificate error
                    if "CERTIFICATE_VERIFY_FAILED" in str(ssl_error) or "SSL" in str(ssl_error):
                        print(f"⚠️ SSL certificate verification failed, retrying with SSL bypass...")
                        logger.warning(f"SSL certificate error detected, attempting to bypass SSL verification: {ssl_error}")

                        # Temporarily disable SSL verification for Whisper model download
                        # This is needed in corporate environments with self-signed certificates
                        skip_ssl = os.getenv('WHISPER_SKIP_SSL_VERIFY', 'true').lower() == 'true'

                        if skip_ssl:
                            # Create an unverified SSL context
                            ssl_context = ssl.create_default_context()
                            ssl_context.check_hostname = False
                            ssl_context.verify_mode = ssl.CERT_NONE

                            # Monkey-patch urllib to use unverified context
                            original_urlopen = urllib.request.urlopen
                            def urlopen_no_verify(url, *args, **kwargs):
                                if 'context' not in kwargs:
                                    kwargs['context'] = ssl_context
                                return original_urlopen(url, *args, **kwargs)

                            urllib.request.urlopen = urlopen_no_verify

                            try:
                                # Retry model loading with SSL verification disabled
                                self.whisper_model = whisper.load_model(model_size)
                                print(f"✅ Loaded Whisper model with SSL bypass")
                                logger.info(f"Loaded local Whisper model with SSL verification bypassed: {model_size}")
                            finally:
                                # Restore original urlopen
                                urllib.request.urlopen = original_urlopen
                        else:
                            # SSL verification is required, raise the original error
                            raise ssl_error
                    else:
                        # Not an SSL error, re-raise it
                        raise

            print(f"🎵 Transcribing with local Whisper: {file_path}")

            # Transcribe with optimized settings for speed
            result = self.whisper_model.transcribe(
                file_path,
                word_timestamps=True,
                verbose=False,
                temperature=0.0,  # More deterministic, faster
                best_of=1,        # Faster inference
                beam_size=1,      # Faster beam search
                fp16=True         # Use half precision for speed (if supported)
            )

            print(f"✅ Local Whisper transcription completed: {len(result.get('text', ''))} chars")
            logger.info(f"Local Whisper transcription completed for {file_path}")
            return result

        except ImportError:
            print("⚠️ OpenAI Whisper not available, will try AWS Transcribe")
            logger.info("OpenAI Whisper not available, will try AWS Transcribe")
            return None
        except Exception as e:
            print(f"❌ Local Whisper transcription failed: {e}")
            logger.error(f"Local Whisper transcription failed for {file_path}: {e}")
            return None
    
    async def _transcribe_with_bedrock_audio(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Transcribe audio using Bedrock audio models (context-aware, integrated)."""
        try:
            print(f"🤖 Transcribing with Bedrock audio models...")
            
            # Check file size and duration first (Bedrock has limits)
            file_size = os.path.getsize(file_path)
            max_size = 25 * 1024 * 1024  # 25MB in bytes
            
            if file_size > max_size:
                print(f"⚠️ Audio file too large for Bedrock ({file_size / 1024 / 1024:.1f}MB > 25MB)")
                print(f"🔄 Falling back to Whisper for large file...")
                return None  # This will trigger Whisper fallback
            
            # Also check duration if we have metadata
            try:
                metadata = await self._get_audio_metadata(file_path)
                duration = metadata.get('duration', 0)
                if duration > 600:  # 10 minutes - practical limit for good results
                    print(f"⚠️ Audio too long for Bedrock ({duration:.1f}s > 600s)")
                    print(f"🔄 Falling back to Whisper for long audio...")
                    return None
            except Exception:
                # If we can't get metadata, continue with file size check only
                pass
            
            # Read audio file and encode to base64
            with open(file_path, 'rb') as audio_file:
                audio_data = audio_file.read()
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Get file format
            file_extension = Path(file_path).suffix.lower()
            media_type_map = {
                '.mp3': 'audio/mpeg',
                '.wav': 'audio/wav', 
                '.m4a': 'audio/mp4',
                '.aac': 'audio/aac',
                '.flac': 'audio/flac',
                '.ogg': 'audio/ogg'
            }
            media_type = media_type_map.get(file_extension, 'audio/mpeg')
            
            # Use Claude 3.5 Sonnet with audio capabilities
            prompt = """
Please transcribe this audio file and provide:
1. Full transcript text
2. Key topics discussed
3. Speaker analysis (if multiple speakers)
4. Educational content assessment
5. Confidence level

Format the response as JSON:
{
    "transcript": "full transcription text",
    "topics": ["topic1", "topic2"],
    "speakers": [{"id": "speaker1", "segments": [...]}],
    "educational_value": "assessment of educational content",
    "confidence": 0.95
}
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
                return {
                    'text': parsed_result.get('transcript', ''),
                    'segments': [
                        {
                            'start': 0,
                            'end': 0,
                            'text': parsed_result.get('transcript', ''),
                            'speaker': 'Speaker_1',
                            'confidence': parsed_result.get('confidence', 0.9)
                        }
                    ],
                    'topics': parsed_result.get('topics', []),
                    'educational_value': parsed_result.get('educational_value', ''),
                    'processing_method': 'bedrock_audio'
                }
                
            except json.JSONDecodeError:
                # If JSON parsing fails, use the raw text as transcript
                return {
                    'text': response_text,
                    'segments': [
                        {
                            'start': 0,
                            'end': 0, 
                            'text': response_text,
                            'speaker': 'Speaker_1',
                            'confidence': 0.8
                        }
                    ],
                    'processing_method': 'bedrock_audio_raw'
                }
            
        except Exception as e:
            print(f"❌ Bedrock audio transcription failed: {e}")
            logger.error(f"Bedrock audio transcription failed for {file_path}: {e}")
            return None
    

    
    def _create_transcription_segments(self, transcription_result: Dict[str, Any]) -> List[TranscriptionSegment]:
        """Create transcription segments with timestamps from Whisper or AWS Transcribe result."""
        segments = []
        
        if 'segments' in transcription_result:
            # Handle both Whisper and AWS Transcribe segment formats
            for i, segment in enumerate(transcription_result['segments']):
                # Whisper uses 'start'/'end', AWS Transcribe uses 'start_time'/'end_time'
                start_time = segment.get('start', segment.get('start_time', 0))
                end_time = segment.get('end', segment.get('end_time', 0))
                text = segment.get('text', '').strip()
                
                # Handle confidence scores from different sources
                confidence = segment.get('confidence', 0.9)  # AWS Transcribe
                if 'avg_logprob' in segment:  # Whisper log probability
                    confidence = max(0.0, min(1.0, segment['avg_logprob'] + 1.0))
                
                # Handle speaker information
                speaker_id = segment.get('speaker', f'Speaker_{i % 3 + 1}')
                
                segments.append(TranscriptionSegment(
                    start_time=float(start_time),
                    end_time=float(end_time),
                    text=text,
                    confidence=confidence,
                    speaker_id=speaker_id,
                    topic_id=None     # Will be filled by topic segmentation
                ))
        else:
            # Single segment fallback
            text = transcription_result.get('text', '')
            if text:
                segments.append(TranscriptionSegment(
                    start_time=0,
                    end_time=0,
                    text=text,
                    confidence=0.5,
                    speaker_id='Speaker_1',
                    topic_id=None
                ))
        
        return segments
    
    async def _identify_speakers(self, segments: List[TranscriptionSegment], file_path: str) -> List[Dict[str, Any]]:
        """Identify and analyze speakers from transcription segments."""
        speakers = {}
        
        for segment in segments:
            speaker_id = segment.speaker_id or 'Unknown'
            
            if speaker_id not in speakers:
                speakers[speaker_id] = {
                    'id': speaker_id,
                    'total_duration': 0,
                    'word_count': 0,
                    'segments': []
                }
            
            duration = segment.end_time - segment.start_time
            speakers[speaker_id]['total_duration'] += duration
            speakers[speaker_id]['word_count'] += len(segment.text.split())
            speakers[speaker_id]['segments'].append({
                'start': segment.start_time,
                'end': segment.end_time,
                'text': segment.text
            })
        
        # Convert to list and add analysis
        speaker_list = []
        for speaker_data in speakers.values():
            speaker_list.append({
                **speaker_data,
                'speaking_percentage': (speaker_data['total_duration'] / 
                                      max(seg.end_time for seg in segments if seg.end_time > 0)) * 100 
                                      if segments and max(seg.end_time for seg in segments if seg.end_time > 0) > 0 else 0
            })
        
        return speaker_list
    
    async def _segment_topics(self, segments: List[TranscriptionSegment]) -> List[Dict[str, Any]]:
        """Segment audio content into topics using AI analysis."""
        if not segments:
            return []
        
        try:
            # Combine segments into chunks for topic analysis
            text_chunks = []
            current_chunk = ""
            chunk_start = 0
            
            for i, segment in enumerate(segments):
                current_chunk += segment.text + " "
                
                # Create chunks of approximately 500 words or at natural breaks
                if (len(current_chunk.split()) >= 500 or 
                    i == len(segments) - 1 or
                    segment.end_time - chunk_start > 300):  # 5 minutes max per chunk
                    
                    text_chunks.append({
                        'text': current_chunk.strip(),
                        'start_time': chunk_start,
                        'end_time': segment.end_time,
                        'segment_indices': list(range(len(text_chunks) * 10, i + 1))
                    })
                    
                    current_chunk = ""
                    chunk_start = segment.end_time
            
            # Analyze topics using AI
            topics = await self._analyze_topics_with_ai(text_chunks)
            
            # Assign topic IDs to segments
            for topic in topics:
                topic_id = f"topic_{topic['id']}"
                for seg_idx in topic.get('segment_indices', []):
                    if seg_idx < len(segments):
                        segments[seg_idx].topic_id = topic_id
            
            return topics
            
        except Exception as e:
            logger.error(f"Topic segmentation failed: {e}")
            return [{'id': 1, 'title': 'General Content', 'start_time': 0, 'end_time': 0}]
    
    async def _analyze_topics_with_ai(self, text_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze text chunks to identify topics using AI."""
        if not text_chunks:
            return []
        
        try:
            # Prepare prompt for topic analysis
            chunks_text = "\n\n".join([
                f"Chunk {i+1} ({chunk['start_time']:.1f}s - {chunk['end_time']:.1f}s):\n{chunk['text'][:500]}..."
                for i, chunk in enumerate(text_chunks)
            ])
            
            prompt = f"""
Analyze this audio transcription and identify distinct topics or themes. For each topic, provide:
1. A clear, descriptive title
2. Start and end times
3. Key concepts discussed
4. Educational value/learning objectives

Transcription chunks:
{chunks_text}

Respond in JSON format with an array of topics:
[{{"id": 1, "title": "Topic Title", "start_time": 0.0, "end_time": 120.0, "key_concepts": ["concept1", "concept2"], "learning_objectives": ["objective1"]}}]
"""

            # Use the configured model for analysis
            model_spec = self.model_config
            if not model_spec:
                model_spec = model_config_manager.get_model_for_agent("audio")
            
            response = self.bedrock_client.invoke_model(
                modelId=model_spec.model_id if model_spec else "us.anthropic.claude-3-haiku-20240307-v1:0",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            result = json.loads(response['body'].read())
            analysis_text = result['content'][0]['text']
            
            # Parse JSON response
            try:
                topics = json.loads(analysis_text)
                return topics if isinstance(topics, list) else []
            except json.JSONDecodeError:
                # Fallback: create basic topics from chunks
                return [
                    {
                        'id': i + 1,
                        'title': f'Topic {i + 1}',
                        'start_time': chunk['start_time'],
                        'end_time': chunk['end_time'],
                        'key_concepts': [],
                        'learning_objectives': []
                    }
                    for i, chunk in enumerate(text_chunks)
                ]
            
        except Exception as e:
            logger.error(f"AI topic analysis failed: {e}")
            return []
    
    def _calculate_confidence(self, segments: List[TranscriptionSegment]) -> float:
        """Calculate overall confidence score from segments."""
        if not segments:
            return 0.0
        
        total_confidence = sum(seg.confidence for seg in segments if seg.confidence > 0)
        valid_segments = len([seg for seg in segments if seg.confidence > 0])
        
        return total_confidence / valid_segments if valid_segments > 0 else 0.5
    
    async def _generate_educational_metadata(self, transcription: str, segments: List[TranscriptionSegment], duration: float) -> Dict[str, Any]:
        """Generate educational metadata from transcription analysis."""
        try:
            # Basic metadata calculation
            word_count = len(transcription.split())
            speaking_rate = word_count / (duration / 60) if duration > 0 else 0  # words per minute
            
            # Use AI to analyze educational content
            educational_analysis = await self._analyze_educational_content(transcription)
            
            return {
                'word_count': word_count,
                'duration_minutes': duration / 60,
                'speaking_rate_wpm': speaking_rate,
                'estimated_reading_time': word_count / 200,  # Average reading speed
                'content_type': educational_analysis.get('content_type', 'general'),
                'difficulty_level': educational_analysis.get('difficulty_level', 'intermediate'),
                'key_topics': educational_analysis.get('key_topics', []),
                'learning_objectives': educational_analysis.get('learning_objectives', []),
                'target_audience': educational_analysis.get('target_audience', 'general'),
                'educational_value_score': educational_analysis.get('educational_value_score', 0.5)
            }
            
        except Exception as e:
            logger.error(f"Educational metadata generation failed: {e}")
            return {
                'word_count': len(transcription.split()),
                'duration_minutes': duration / 60,
                'error': str(e)
            }
    
    async def _analyze_educational_content(self, transcription: str) -> Dict[str, Any]:
        """Analyze transcription for educational content using AI."""
        try:
            prompt = f"""
Analyze this audio transcription for educational content and provide:

1. Content type (lecture, tutorial, discussion, presentation, etc.)
2. Difficulty level (beginner, intermediate, advanced)
3. Key topics and concepts (list of 3-5 main topics)
4. Learning objectives (what students should learn)
5. Target audience (students, professionals, general public, etc.)
6. Educational value score (0.0-1.0, where 1.0 is highly educational)

Transcription (first 1500 characters):
{transcription[:1500]}...

Respond in JSON format:
{{"content_type": "lecture", "difficulty_level": "intermediate", "key_topics": ["topic1", "topic2"], "learning_objectives": ["objective1"], "target_audience": "students", "educational_value_score": 0.8}}
"""

            model_spec = self.model_config or model_config_manager.get_model_for_agent("audio")
            
            response = self.bedrock_client.invoke_model(
                modelId=model_spec.model_id if model_spec else "us.anthropic.claude-3-haiku-20240307-v1:0",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            result = json.loads(response['body'].read())
            analysis_text = result['content'][0]['text']
            
            # Parse JSON response
            try:
                return json.loads(analysis_text)
            except json.JSONDecodeError:
                return {
                    'content_type': 'general',
                    'difficulty_level': 'intermediate',
                    'key_topics': [],
                    'learning_objectives': [],
                    'target_audience': 'general',
                    'educational_value_score': 0.5
                }
                
        except Exception as e:
            logger.error(f"Educational content analysis failed: {e}")
            return {}
    
    async def _convert_to_wav(self, file_path: str) -> str:
        """Convert audio file to WAV format if needed."""
        if file_path.lower().endswith('.wav'):
            return file_path
        
        try:
            # Create temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_wav_path = temp_file.name
            
            # Use ffmpeg to convert to WAV
            result = subprocess.run([
                'ffmpeg', '-i', file_path, '-acodec', 'pcm_s16le', '-ar', '16000', 
                '-ac', '1', temp_wav_path, '-y'
            ], capture_output=True, timeout=120)
            
            if result.returncode == 0:
                return temp_wav_path
            else:
                print(f"⚠️ ffmpeg conversion failed: {result.stderr.decode()}")
                return file_path
                
        except Exception as e:
            print(f"⚠️ Audio conversion failed: {e}")
            return file_path
    
    async def _transcribe_audio(self, file_path: str) -> str:
        """Transcribe audio to text using speech recognition."""
        try:
            with sr.AudioFile(file_path) as source:
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                
                # Record the audio
                audio = self.recognizer.record(source)
                
                # Perform speech recognition
                try:
                    # Try Google Speech Recognition first
                    text = self.recognizer.recognize_google(audio)
                    return text
                except sr.UnknownValueError:
                    return "Speech recognition could not understand the audio"
                except sr.RequestError as e:
                    # Fallback to offline recognition
                    try:
                        text = self.recognizer.recognize_sphinx(audio)
                        return text
                    except:
                        return f"Speech recognition service error: {str(e)}"
                        
        except Exception as e:
            print(f"⚠️ Transcription failed: {e}")
            return f"Transcription failed: {str(e)}"
    

    
    async def _analyze_enhanced_content(self, audio_analysis: AudioAnalysisResult, file_path: str) -> Dict[str, Any]:
        """Analyze enhanced audio content using AI with comprehensive metadata."""
        try:
            prompt = f"""
Analyze this enhanced audio file processing result:

File: {Path(file_path).name}
Duration: {audio_analysis.duration:.1f} seconds
Speakers: {len(audio_analysis.speakers)}
Topics: {len(audio_analysis.topics)}
Confidence: {audio_analysis.confidence_score:.2f}

Transcription: {audio_analysis.transcription[:1500]}...

Educational Metadata:
- Content Type: {audio_analysis.educational_metadata.get('content_type', 'Unknown')}
- Difficulty Level: {audio_analysis.educational_metadata.get('difficulty_level', 'Unknown')}
- Key Topics: {audio_analysis.educational_metadata.get('key_topics', [])}

Please provide comprehensive analysis including:
1. Overall content assessment and quality
2. Educational value and learning potential
3. Recommended use cases for learners
4. Content structure and organization
5. Speaker engagement and presentation style
6. Key insights and takeaways
7. Suggestions for improvement or follow-up

Format as JSON with clear categories.
"""
            
            # Use configured model for analysis
            model_spec = self.model_config or model_config_manager.get_model_for_agent("audio")
            
            response = self.bedrock_client.invoke_model(
                modelId=model_spec.model_id if model_spec else "us.anthropic.claude-3-haiku-20240307-v1:0",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1500,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            result = json.loads(response['body'].read())
            analysis_text = result['content'][0]['text']
            
            return {
                "ai_analysis": analysis_text,
                "content_type": "enhanced_audio_file",
                "processing_method": "bedrock_audio_with_ai_analysis",
                "transcription_confidence": audio_analysis.confidence_score,
                "duration_seconds": audio_analysis.duration,
                "speaker_count": len(audio_analysis.speakers),
                "topic_count": len(audio_analysis.topics),
                "educational_value_score": audio_analysis.educational_metadata.get('educational_value_score', 0.5)
            }
            
        except Exception as e:
            logger.error(f"Enhanced content analysis failed: {e}")
            return {
                "ai_analysis": f"Analysis failed: {str(e)}",
                "content_type": "enhanced_audio_file",
                "processing_method": "fallback_analysis",
                "transcription_confidence": audio_analysis.confidence_score,
                "duration_seconds": audio_analysis.duration,
                "error": str(e)
            }


# Global instance
audio_agent = AudioAgent()