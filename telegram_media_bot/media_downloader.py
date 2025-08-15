#!/usr/bin/env python3
"""
Media downloader module for MediaFetch bot
Handles downloading media from various platforms using yt-dlp
"""

import os
import logging
import asyncio
import tempfile
from typing import Dict, Any, Optional
from pathlib import Path

import yt_dlp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .config import Config
from .utils import sanitize_filename, validate_url

logger = logging.getLogger(__name__)

class MediaDownloader:
    """Handles media downloads from various platforms"""
    
    def __init__(self):
        """Initialize the media downloader"""
        self.config = Config()
        self.download_config = self.config.get_download_config()
        self.storage_config = self.config.get_storage_config()
        
        # Create temporary directory for downloads
        self.temp_dir = Path(self.storage_config['temp_dir'])
        self.temp_dir.mkdir(exist_ok=True)
        
        logger.info(f"MediaDownloader initialized with temp dir: {self.temp_dir}")
    
    async def download_media(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Download media from the given URL
        
        Args:
            url: Media URL to download
            
        Returns:
            Dictionary containing download information or None if failed
        """
        if not validate_url(url):
            raise ValueError(f"Invalid URL: {url}")
        
        # Check if domain is allowed/blocked
        if not self._is_domain_allowed(url):
            raise ValueError(f"Domain not allowed: {url}")
        
        try:
            # Run download in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self._download_media_sync, url
            )
            return result
            
        except Exception as e:
            logger.error(f"Failed to download media from {url}: {e}")
            raise
    
    def _download_media_sync(self, url: str) -> Optional[Dict[str, Any]]:
        """Synchronous download method (runs in thread pool)"""
        try:
            # Configure yt-dlp options
            ydl_opts = self._get_ydl_options(url)
            
            # Extract info first
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    raise Exception("Failed to extract media information")
                
                # Check file size limits
                if 'filesize' in info and info['filesize']:
                    if info['filesize'] > self.storage_config['max_file_size']:
                        raise ValueError(
                            f"File too large: {info['filesize']} bytes "
                            f"(max: {self.storage_config['max_file_size']} bytes)"
                        )
                
                # Download the media
                ydl.download([url])
                
                # Get the downloaded file path
                file_path = ydl.prepare_filename(info)
                
                if not os.path.exists(file_path):
                    raise Exception("Downloaded file not found")
                
                # Get file size
                file_size = os.path.getsize(file_path)
                
                # Return download information
                return {
                    'file_path': file_path,
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration'),
                    'file_size': file_size,
                    'format': info.get('format', 'Unknown'),
                    'quality': info.get('format_note', 'Best available'),
                    'extractor': info.get('extractor', 'Unknown'),
                    'url': url
                }
                
        except Exception as e:
            logger.error(f"Download failed for {url}: {e}")
            raise
    
    def _get_ydl_options(self, url: str) -> Dict[str, Any]:
        """Get yt-dlp options based on configuration"""
        # Create unique filename
        temp_filename = f"mediafetch_%(title)s.%(ext)s"
        
        ydl_opts = {
            'outtmpl': str(self.temp_dir / temp_filename),
            'format': self.download_config['format_preference'],
            'timeout': self.download_config['timeout'],
            'retries': self.download_config['max_retries'],
            'user_agent': self.download_config['user_agent'],
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'nocheckcertificate': True,  # For Heroku compatibility
            'ignoreerrors': False,
            'no_color': True,
            'geo_bypass': True,
            'geo_bypass_country': 'US',
            'prefer_ffmpeg': True,
            'postprocessors': []
        }
        
        # Add format-specific options
        if 'youtube' in url.lower():
            ydl_opts.update({
                'format': 'best[height<=720]/best',  # Limit to 720p for Heroku
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4'
                }]
            })
        elif 'tiktok' in url.lower():
            ydl_opts.update({
                'format': 'best',
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4'
                }]
            })
        elif 'instagram' in url.lower():
            ydl_opts.update({
                'format': 'best',
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4'
                }]
            })
        
        return ydl_opts
    
    def _is_domain_allowed(self, url: str) -> bool:
        """Check if the domain is allowed for downloads"""
        security_config = self.config.get_security_config()
        
        # Check blocked domains first
        for blocked_domain in security_config['blocked_domains']:
            if blocked_domain.strip() and blocked_domain.strip() in url:
                return False
        
        # Check allowed domains (if specified)
        allowed_domains = security_config['allowed_domains']
        if allowed_domains and any(domain.strip() for domain in allowed_domains):
            return any(domain.strip() in url for domain in allowed_domains)
        
        # If no restrictions specified, allow all
        return True
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError))
    )
    async def download_with_retry(self, url: str) -> Optional[Dict[str, Any]]:
        """Download media with automatic retry logic"""
        return await self.download_media(url)
    
    def get_supported_platforms(self) -> list:
        """Get list of supported media platforms"""
        return [
            'YouTube',
            'TikTok', 
            'Instagram',
            'Vimeo',
            'Twitter',
            'Facebook',
            'Reddit',
            'SoundCloud',
            'Spotify',
            'Apple Music'
        ]
    
    def cleanup_temp_files(self):
        """Clean up temporary download files"""
        try:
            for file_path in self.temp_dir.glob("mediafetch_*"):
                if file_path.is_file():
                    file_path.unlink()
                    logger.debug(f"Cleaned up temp file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp files: {e}")
    
    def get_download_stats(self) -> Dict[str, Any]:
        """Get download statistics"""
        temp_files = list(self.temp_dir.glob("mediafetch_*"))
        total_size = sum(f.stat().st_size for f in temp_files if f.is_file())
        
        return {
            'temp_files_count': len(temp_files),
            'temp_files_size': total_size,
            'temp_dir': str(self.temp_dir),
            'max_file_size': self.storage_config['max_file_size']
        }
