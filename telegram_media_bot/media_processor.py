#!/usr/bin/env python3
"""
Media processor module for MediaFetch bot
Handles media processing, compression, and optimization for Heroku deployment
"""

import os
import logging
import asyncio
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path

from .config import Config

logger = logging.getLogger(__name__)

class MediaProcessor:
    """Handles media processing and optimization"""
    
    def __init__(self):
        """Initialize the media processor"""
        self.config = Config()
        self.storage_config = self.config.get_storage_config()
        
        # Check if FFmpeg is available
        self.ffmpeg_available = self._check_ffmpeg()
        if not self.ffmpeg_available:
            logger.warning("FFmpeg not available - media processing will be limited")
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available on the system"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False
    
    async def process_media(self, file_path: str, file_size: int) -> str:
        """
        Process media file based on size and type
        
        Args:
            file_path: Path to the media file
            file_size: Size of the file in bytes
            
        Returns:
            Path to the processed file (may be the same as input)
        """
        try:
            # Check if processing is needed
            if not self._needs_processing(file_path, file_size):
                return file_path
            
            # Process the media
            processed_file = await self._process_media_file(file_path, file_size)
            
            if processed_file and os.path.exists(processed_file):
                # Clean up original file if it's different
                if processed_file != file_path and os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Cleaned up original file: {file_path}")
                
                return processed_file
            else:
                logger.warning("Media processing failed, returning original file")
                return file_path
                
        except Exception as e:
            logger.error(f"Media processing failed: {e}")
            return file_path
    
    def _needs_processing(self, file_path: str, file_size: int) -> bool:
        """Determine if media processing is needed"""
        if not self.ffmpeg_available:
            return False
        
        # Check file size threshold (50MB for Heroku)
        if file_size > 50 * 1024 * 1024:
            return True
        
        # Check file extension
        file_ext = Path(file_path).suffix.lower()
        processable_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
        
        return file_ext in processable_extensions
    
    async def _process_media_file(self, file_path: str, file_size: int) -> Optional[str]:
        """Process the media file with FFmpeg"""
        try:
            # Run processing in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self._process_media_sync, file_path, file_size
            )
            return result
            
        except Exception as e:
            logger.error(f"Media processing failed: {e}")
            return None
    
    def _process_media_sync(self, file_path: str, file_size: int) -> Optional[str]:
        """Synchronous media processing method"""
        try:
            file_path_obj = Path(file_path)
            output_path = file_path_obj.parent / f"processed_{file_path_obj.name}"
            
            # Determine processing parameters based on file size
            if file_size > 100 * 1024 * 1024:  # > 100MB
                # Aggressive compression for very large files
                video_codec = 'libx264'
                crf = '28'  # Higher compression
                audio_codec = 'aac'
                audio_bitrate = '128k'
            elif file_size > 50 * 1024 * 1024:  # > 50MB
                # Moderate compression
                video_codec = 'libx264'
                crf = '23'  # Balanced quality/size
                audio_codec = 'aac'
                audio_bitrate = '192k'
            else:
                # Light compression for smaller files
                video_codec = 'libx264'
                crf = '20'  # High quality
                audio_codec = 'aac'
                audio_bitrate = '256k'
            
            # Build FFmpeg command
            cmd = [
                'ffmpeg',
                '-i', file_path,
                '-c:v', video_codec,
                '-crf', crf,
                '-preset', 'fast',  # Faster encoding for Heroku
                '-c:a', audio_codec,
                '-b:a', audio_bitrate,
                '-movflags', '+faststart',  # Optimize for streaming
                '-y',  # Overwrite output file
                str(output_path)
            ]
            
            # Execute FFmpeg command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0 and output_path.exists():
                logger.info(f"Media processed successfully: {output_path}")
                return str(output_path)
            else:
                logger.error(f"FFmpeg failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("Media processing timed out")
            return None
        except Exception as e:
            logger.error(f"Media processing error: {e}")
            return None
    
    async def optimize_for_telegram(self, file_path: str) -> str:
        """Optimize media specifically for Telegram's requirements"""
        try:
            # Check Telegram file size limits
            file_size = os.path.getsize(file_path)
            
            if file_size <= 50 * 1024 * 1024:  # <= 50MB
                return file_path  # No optimization needed
            
            # Optimize for Telegram's 50MB limit
            optimized_file = await self._optimize_for_size(file_path, 50 * 1024 * 1024)
            
            if optimized_file and os.path.exists(optimized_file):
                return optimized_file
            else:
                logger.warning("Telegram optimization failed, returning original")
                return file_path
                
        except Exception as e:
            logger.error(f"Telegram optimization failed: {e}")
            return file_path
    
    async def _optimize_for_size(self, file_path: str, target_size: int) -> Optional[str]:
        """Optimize media to fit within target size"""
        try:
            # Run optimization in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self._optimize_for_size_sync, file_path, target_size
            )
            return result
            
        except Exception as e:
            logger.error(f"Size optimization failed: {e}")
            return None
    
    def _optimize_for_size_sync(self, file_path: str, target_size: int) -> Optional[str]:
        """Synchronous size optimization method"""
        try:
            file_path_obj = Path(file_path)
            output_path = file_path_obj.parent / f"telegram_optimized_{file_path_obj.name}"
            
            # Start with high quality and reduce if needed
            crf_values = [23, 26, 28, 30, 32]
            
            for crf in crf_values:
                cmd = [
                    'ffmpeg',
                    '-i', file_path,
                    '-c:v', 'libx264',
                    '-crf', str(crf),
                    '-preset', 'fast',
                    '-c:a', 'aac',
                    '-b:a', '128k',
                    '-movflags', '+faststart',
                    '-y',
                    str(output_path)
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=180
                )
                
                if result.returncode == 0 and output_path.exists():
                    output_size = os.path.getsize(output_path)
                    
                    if output_size <= target_size:
                        logger.info(f"Optimization successful with CRF {crf}: {output_size} bytes")
                        return str(output_path)
                    else:
                        # Remove oversized file and try next CRF
                        output_path.unlink()
                        continue
            
            logger.warning("Could not optimize to target size")
            return None
            
        except Exception as e:
            logger.error(f"Size optimization error: {e}")
            return None
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get media processing statistics"""
        return {
            'ffmpeg_available': self.ffmpeg_available,
            'max_file_size': self.storage_config['max_file_size'],
            'telegram_limit': 50 * 1024 * 1024,  # 50MB
            'supported_formats': ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        }
    
    def cleanup_processed_files(self):
        """Clean up processed media files"""
        try:
            temp_dir = Path(self.storage_config['temp_dir'])
            
            # Remove processed files
            for pattern in ['processed_*', 'telegram_optimized_*']:
                for file_path in temp_dir.glob(pattern):
                    if file_path.is_file():
                        file_path.unlink()
                        logger.debug(f"Cleaned up processed file: {file_path}")
                        
        except Exception as e:
            logger.warning(f"Failed to cleanup processed files: {e}")
