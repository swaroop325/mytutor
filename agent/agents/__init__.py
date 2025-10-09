"""
MyTutor Specialized Agents Package

This package contains specialized agents for processing different types of content:
- TextAgent: Text documents (TXT, DOCX, PPT, etc.)
- PDFAgent: PDF documents
- VideoAgent: Video files (MP4, AVI, MOV, etc.)
- AudioAgent: Audio files (MP3, WAV, M4A, etc.)
- ImageAgent: Image files (JPG, PNG, GIF, etc.)
"""

from .text_agent import TextAgent, text_agent
from .pdf_agent import PDFAgent, pdf_agent
from .video_agent import VideoAgent, video_agent
from .audio_agent import AudioAgent, audio_agent
from .image_agent import ImageAgent, image_agent

__all__ = [
    'TextAgent', 'text_agent',
    'PDFAgent', 'pdf_agent', 
    'VideoAgent', 'video_agent',
    'AudioAgent', 'audio_agent',
    'ImageAgent', 'image_agent'
]