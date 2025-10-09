import re
import httpx
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime


class LinkValidationService:
    """Service for validating and analyzing direct resource links."""
    
    # Supported platforms and their patterns
    PLATFORM_PATTERNS = {
        'youtube': [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
            r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]+)',
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)'
        ],
        'vimeo': [
            r'(?:https?://)?(?:www\.)?vimeo\.com/(\d+)',
            r'(?:https?://)?player\.vimeo\.com/video/(\d+)'
        ],
        'coursera': [
            r'(?:https?://)?(?:www\.)?coursera\.org/learn/([^/]+)',
            r'(?:https?://)?(?:www\.)?coursera\.org/course/([^/]+)'
        ],
        'udemy': [
            r'(?:https?://)?(?:www\.)?udemy\.com/course/([^/]+)'
        ],
        'edx': [
            r'(?:https?://)?(?:www\.)?edx\.org/course/([^/]+)'
        ]
    }
    
    # File type patterns
    FILE_TYPE_PATTERNS = {
        'pdf': r'\.pdf(?:\?.*)?$',
        'video': r'\.(mp4|avi|mov|mkv|webm|flv)(?:\?.*)?$',
        'audio': r'\.(mp3|wav|m4a|aac|ogg|flac)(?:\?.*)?$',
        'document': r'\.(docx?|pptx?|xlsx?|txt|rtf)(?:\?.*)?$',
        'image': r'\.(jpe?g|png|gif|webp|svg|bmp)(?:\?.*)?$',
        'archive': r'\.(zip|rar|7z|tar|gz)(?:\?.*)?$'
    }
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
    
    def validate_url_format(self, url: str) -> Tuple[bool, Optional[str]]:
        """Validate URL format."""
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False, "Invalid URL format"
            
            if parsed.scheme not in ['http', 'https']:
                return False, "Only HTTP and HTTPS URLs are supported"
            
            return True, None
        except Exception as e:
            return False, f"URL parsing error: {str(e)}"
    
    def detect_platform(self, url: str) -> Optional[str]:
        """Detect the platform/service from URL."""
        url_lower = url.lower()
        
        for platform, patterns in self.PLATFORM_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url_lower, re.IGNORECASE):
                    return platform
        
        return None
    
    def detect_file_type(self, url: str) -> Optional[str]:
        """Detect file type from URL."""
        url_lower = url.lower()
        
        for file_type, pattern in self.FILE_TYPE_PATTERNS.items():
            if re.search(pattern, url_lower, re.IGNORECASE):
                return file_type
        
        return None
    
    def get_resource_type(self, url: str) -> str:
        """Determine the type of resource."""
        platform = self.detect_platform(url)
        if platform:
            return f"{platform}_content"
        
        file_type = self.detect_file_type(url)
        if file_type:
            return f"{file_type}_file"
        
        return "web_resource"
    
    async def check_url_accessibility(self, url: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Check if URL is accessible and get metadata."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Use HEAD request first to check accessibility
                try:
                    response = await client.head(url, follow_redirects=True)
                    status_code = response.status_code
                except httpx.RequestError:
                    # If HEAD fails, try GET with limited content
                    response = await client.get(url, follow_redirects=True)
                    status_code = response.status_code
                
                if status_code >= 400:
                    return False, f"HTTP {status_code} error", None
                
                # Extract metadata
                metadata = {
                    "status_code": status_code,
                    "content_type": response.headers.get("content-type", ""),
                    "content_length": response.headers.get("content-length"),
                    "final_url": str(response.url),
                    "server": response.headers.get("server", ""),
                    "last_modified": response.headers.get("last-modified")
                }
                
                # For HTML content, try to get title
                if "text/html" in metadata["content_type"]:
                    try:
                        # Get a small portion of the content to extract title
                        content_response = await client.get(url, follow_redirects=True)
                        content = content_response.text[:2000]  # First 2KB
                        
                        # Extract title using regex
                        title_match = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE)
                        if title_match:
                            metadata["title"] = title_match.group(1).strip()
                    except:
                        pass  # Title extraction is optional
                
                return True, None, metadata
                
        except httpx.TimeoutException:
            return False, "Request timeout", None
        except httpx.RequestError as e:
            return False, f"Request error: {str(e)}", None
        except Exception as e:
            return False, f"Unexpected error: {str(e)}", None
    
    def assess_security_risk(self, url: str, metadata: Optional[Dict[str, Any]] = None) -> Tuple[str, List[str]]:
        """Assess security risk level of the URL."""
        warnings = []
        risk_level = "low"
        
        parsed = urlparse(url)
        
        # Check for suspicious domains
        suspicious_tlds = ['.tk', '.ml', '.ga', '.cf', '.bit']
        if any(parsed.netloc.endswith(tld) for tld in suspicious_tlds):
            warnings.append("Suspicious top-level domain")
            risk_level = "medium"
        
        # Check for IP addresses instead of domains
        if re.match(r'^\d+\.\d+\.\d+\.\d+', parsed.netloc):
            warnings.append("Direct IP address instead of domain")
            risk_level = "medium"
        
        # Check for non-HTTPS
        if parsed.scheme == 'http':
            warnings.append("Non-secure HTTP connection")
            if risk_level == "low":
                risk_level = "medium"
        
        # Check for suspicious file extensions
        suspicious_extensions = ['.exe', '.bat', '.cmd', '.scr', '.pif', '.com', '.jar']
        if any(url.lower().endswith(ext) for ext in suspicious_extensions):
            warnings.append("Potentially dangerous file type")
            risk_level = "high"
        
        # Check for URL shorteners
        shorteners = ['bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'ow.ly', 'short.link']
        if any(shortener in parsed.netloc for shortener in shorteners):
            warnings.append("URL shortener detected - final destination unknown")
            risk_level = "medium"
        
        return risk_level, warnings
    
    async def validate_single_link(self, url: str) -> Dict[str, Any]:
        """Validate a single link and return comprehensive information."""
        result = {
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "valid": False,
            "accessible": False,
            "resource_type": "unknown",
            "platform": None,
            "file_type": None,
            "security_risk": "unknown",
            "security_warnings": [],
            "error": None,
            "metadata": {}
        }
        
        # Validate URL format
        is_valid_format, format_error = self.validate_url_format(url)
        if not is_valid_format:
            result["error"] = format_error
            return result
        
        result["valid"] = True
        
        # Detect platform and file type
        result["platform"] = self.detect_platform(url)
        result["file_type"] = self.detect_file_type(url)
        result["resource_type"] = self.get_resource_type(url)
        
        # Assess security
        risk_level, warnings = self.assess_security_risk(url)
        result["security_risk"] = risk_level
        result["security_warnings"] = warnings
        
        # Check accessibility
        is_accessible, access_error, metadata = await self.check_url_accessibility(url)
        result["accessible"] = is_accessible
        if access_error:
            result["error"] = access_error
        if metadata:
            result["metadata"] = metadata
        
        return result
    
    async def validate_multiple_links(self, links: List[str]) -> Dict[str, Any]:
        """Validate multiple links and return batch results."""
        results = {
            "total_links": len(links),
            "valid_links": 0,
            "accessible_links": 0,
            "high_risk_links": 0,
            "results": [],
            "summary": {
                "platforms": {},
                "file_types": {},
                "security_risks": {"low": 0, "medium": 0, "high": 0}
            }
        }
        
        # Process each link
        for url in links:
            link_result = await self.validate_single_link(url)
            results["results"].append(link_result)
            
            # Update counters
            if link_result["valid"]:
                results["valid_links"] += 1
            
            if link_result["accessible"]:
                results["accessible_links"] += 1
            
            if link_result["security_risk"] == "high":
                results["high_risk_links"] += 1
            
            # Update summary
            if link_result["platform"]:
                platform = link_result["platform"]
                results["summary"]["platforms"][platform] = results["summary"]["platforms"].get(platform, 0) + 1
            
            if link_result["file_type"]:
                file_type = link_result["file_type"]
                results["summary"]["file_types"][file_type] = results["summary"]["file_types"].get(file_type, 0) + 1
            
            risk_level = link_result["security_risk"]
            if risk_level in results["summary"]["security_risks"]:
                results["summary"]["security_risks"][risk_level] += 1
        
        return results


# Global instance
link_validation_service = LinkValidationService()