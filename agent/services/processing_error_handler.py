"""
Processing Error Handler System
Handles error categorization, logging, and recovery for file processing operations
"""
import logging
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import traceback

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categories of processing errors."""
    CONNECTION = "connection"
    DEPENDENCY = "dependency"
    FILE_ACCESS = "file_access"
    PROCESSING = "processing"
    THROTTLING = "throttling"
    CONFIGURATION = "configuration"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class ProcessingErrorHandler:
    """Handles processing errors with categorization and recovery suggestions."""
    
    def __init__(self):
        self.error_count = 0
        self.error_history = []
        self.max_history = 100
    
    def log_processing_error(self, error: Exception, context: Dict[str, Any]) -> str:
        """
        Log a processing error with full context and return error ID.
        
        Args:
            error: The exception that occurred
            context: Context information about the error
            
        Returns:
            Unique error ID for tracking
        """
        self.error_count += 1
        error_id = f"error_{int(time.time())}_{self.error_count}"
        
        # Categorize the error
        category = self.categorize_error(error)
        
        # Create error record
        error_record = {
            "error_id": error_id,
            "timestamp": datetime.now().isoformat(),
            "category": category.value,
            "error_type": type(error).__name__,
            "message": str(error),
            "context": context,
            "traceback": traceback.format_exc(),
            "remediation_steps": self.get_remediation_steps(category)
        }
        
        # Add to history
        self.error_history.append(error_record)
        if len(self.error_history) > self.max_history:
            self.error_history.pop(0)
        
        # Log the error
        logger.error(f"Processing error {error_id}: {error}", extra={
            "error_id": error_id,
            "category": category.value,
            "context": context
        })
        
        return error_id
    
    def categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize an error based on its type and message."""
        error_str = str(error).lower()
        error_type = type(error).__name__
        
        # Connection errors
        if any(keyword in error_str for keyword in ['connection', 'connect', 'network', 'timeout']):
            return ErrorCategory.CONNECTION
        
        # Throttling errors (AWS Bedrock)
        if 'throttling' in error_str or 'too many requests' in error_str:
            return ErrorCategory.THROTTLING
        
        # Dependency errors
        if error_type in ['ImportError', 'ModuleNotFoundError'] or 'no module named' in error_str:
            return ErrorCategory.DEPENDENCY
        
        # File access errors
        if error_type in ['FileNotFoundError', 'PermissionError'] or any(keyword in error_str for keyword in ['file not found', 'permission denied', 'no such file']):
            return ErrorCategory.FILE_ACCESS
        
        # Configuration errors
        if any(keyword in error_str for keyword in ['credentials', 'access denied', 'unauthorized', 'invalid region']):
            return ErrorCategory.CONFIGURATION
        
        # Timeout errors
        if 'timeout' in error_str or error_type == 'TimeoutError':
            return ErrorCategory.TIMEOUT
        
        # Processing errors (general)
        if any(keyword in error_str for keyword in ['processing', 'analysis', 'extraction']):
            return ErrorCategory.PROCESSING
        
        return ErrorCategory.UNKNOWN
    
    def get_remediation_steps(self, category: ErrorCategory) -> List[str]:
        """Get remediation steps for a specific error category."""
        remediation_map = {
            ErrorCategory.CONNECTION: [
                "Check if AgentCore runtime is running",
                "Verify network connectivity",
                "Check firewall settings and port accessibility",
                "Restart AgentCore service if needed"
            ],
            ErrorCategory.THROTTLING: [
                "Wait before retrying the request",
                "Implement exponential backoff for retries",
                "Consider processing fewer files simultaneously",
                "Check AWS Bedrock service limits and quotas"
            ],
            ErrorCategory.DEPENDENCY: [
                "Install missing Python packages using pip",
                "Check system dependencies (tesseract, ffmpeg, etc.)",
                "Verify virtual environment is activated",
                "Run dependency validation checks"
            ],
            ErrorCategory.FILE_ACCESS: [
                "Verify file exists at the specified path",
                "Check file permissions and ownership",
                "Ensure file is not corrupted or in use",
                "Validate file path resolution logic"
            ],
            ErrorCategory.CONFIGURATION: [
                "Check AWS credentials configuration",
                "Verify AWS region settings",
                "Validate environment variables",
                "Check service configuration files"
            ],
            ErrorCategory.TIMEOUT: [
                "Increase timeout values for large files",
                "Process files in smaller batches",
                "Check system resources and performance",
                "Consider using asynchronous processing"
            ],
            ErrorCategory.PROCESSING: [
                "Check input file format and validity",
                "Verify processing parameters",
                "Review agent-specific logs for details",
                "Try processing with different settings"
            ],
            ErrorCategory.UNKNOWN: [
                "Check system logs for additional details",
                "Verify all system components are operational",
                "Contact support with error details",
                "Try processing with minimal configuration"
            ]
        }
        
        return remediation_map.get(category, ["Contact support with error details"])
    
    def create_error_response(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create a standardized error response."""
        error_id = self.log_processing_error(error, context)
        category = self.categorize_error(error)
        
        return {
            "status": "error",
            "error_id": error_id,
            "error_type": type(error).__name__,
            "category": category.value,
            "message": str(error),
            "timestamp": datetime.now().isoformat(),
            "context": context,
            "remediation_steps": self.get_remediation_steps(category),
            "debug_info": {
                "traceback": traceback.format_exc(),
                "error_count": self.error_count
            }
        }
    
    def handle_throttling_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Special handling for AWS throttling errors."""
        return {
            "status": "throttled",
            "error_type": "ThrottlingException",
            "category": ErrorCategory.THROTTLING.value,
            "message": "AWS Bedrock request was throttled - too many requests",
            "retry_after": 60,  # Suggest waiting 60 seconds
            "context": context,
            "remediation_steps": [
                "Wait 60 seconds before retrying",
                "Process fewer files simultaneously",
                "Implement exponential backoff in retry logic",
                "Consider upgrading AWS service limits if this persists"
            ],
            "partial_success": context.get("partial_success", False)
        }
    
    def collect_debug_info(self) -> Dict[str, Any]:
        """Collect comprehensive debug information."""
        import os
        import sys
        import psutil
        
        try:
            return {
                "system_info": {
                    "python_version": sys.version,
                    "platform": sys.platform,
                    "working_directory": os.getcwd(),
                    "memory_usage": psutil.virtual_memory()._asdict(),
                    "cpu_usage": psutil.cpu_percent(interval=1)
                },
                "error_statistics": {
                    "total_errors": self.error_count,
                    "recent_errors": len(self.error_history),
                    "error_categories": self._get_error_category_stats()
                },
                "environment": {
                    "aws_region": os.getenv("AWS_REGION", "not set"),
                    "has_aws_credentials": bool(os.getenv("AWS_ACCESS_KEY_ID")),
                    "agent_directory": os.path.exists("agent"),
                    "backend_directory": os.path.exists("backend")
                }
            }
        except Exception as e:
            return {
                "debug_collection_error": str(e),
                "basic_info": {
                    "error_count": self.error_count,
                    "python_version": sys.version_info[:3]
                }
            }
    
    def _get_error_category_stats(self) -> Dict[str, int]:
        """Get statistics on error categories."""
        category_counts = {}
        for error_record in self.error_history:
            category = error_record["category"]
            category_counts[category] = category_counts.get(category, 0) + 1
        return category_counts
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent error records."""
        return self.error_history[-limit:] if self.error_history else []


# Global error handler instance
processing_error_handler = ProcessingErrorHandler()