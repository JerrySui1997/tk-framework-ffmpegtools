# python/tk_framework_ffmpeg/ffmpeg_wrapper.py

import subprocess
import os
import json
import re
import sgtk

class FFmpegWrapper(object):
    """
    Wrapper class for FFmpeg and FFprobe operations
    """
    
    def __init__(self, framework):
        """
        Initialize with framework instance
        
        :param framework: The FFmpeg framework instance
        """
        self._framework = framework
        self._logger = framework.logger
        
        # Find our own paths to FFmpeg and FFprobe
        self._ffmpeg_path = self._get_bundled_ffmpeg_path()
        self._ffprobe_path = self._get_bundled_ffprobe_path()
        
        # Set our own default values
        self._max_threads = 4
        self._default_video_codec = "libx264"
        self._default_audio_codec = "aac"
        
        self._logger.info("FFmpeg path: %s" % self._ffmpeg_path)
        self._logger.info("FFprobe path: %s" % self._ffprobe_path)
    
    def _get_bundled_ffmpeg_path(self):
        """Get path to bundled FFmpeg executable (Windows only)"""
        # Get the directory where this file is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up one level from python/ to V1.0.0/, then down to resources/ffmpeg/win/
        bundled_path = os.path.join(
            current_dir,  # .../python/
            "..",         # .../V1.0.0/
            "resources", 
            "ffmpeg", 
            "win", 
            "ffmpeg.exe"
        )
        
        return os.path.normpath(bundled_path)
    
    def _get_bundled_ffprobe_path(self):
        """Get path to bundled FFprobe executable (Windows only)"""
        # Get the directory where this file is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up one level from python/ to V1.0.0/, then down to resources/ffmpeg/win/
        bundled_path = os.path.join(
            current_dir,  # .../python/
            "..",         # .../V1.0.0/
            "resources", 
            "ffmpeg", 
            "win", 
            "ffprobe.exe"
        )
        
        return os.path.normpath(bundled_path)
    
    def execute_ffmpeg_command(self, args, **kwargs):
        """
        Execute FFmpeg command with given arguments
        
        :param args: List of arguments to pass to FFmpeg
        :param kwargs: Additional keyword arguments for subprocess
        :returns: subprocess.CompletedProcess object
        """
        cmd = [self._ffmpeg_path] + args
        
        # Add threading if specified
        if self._max_threads > 0:
            cmd.extend(["-threads", str(self._max_threads)])
        
        self._logger.debug("Executing FFmpeg command: %s" % " ".join(cmd))
        
        try:
            result = subprocess.run(cmd, **kwargs)
            if result.returncode != 0:
                self._logger.error("FFmpeg command failed with return code %s" % result.returncode)
                if hasattr(result, 'stderr') and result.stderr:
                    self._logger.error("FFmpeg stderr: %s" % result.stderr)
            return result
        except Exception as e:
            self._logger.error("FFmpeg command failed: %s" % str(e))
            raise
            
    def execute_ffmpeg_with_progress(self, args, progress_callback=None, **kwargs):
        """
        Execute FFmpeg command with progress monitoring and UI updates
        
        :param args: List of arguments to pass to FFmpeg
        :param progress_callback: Function to call with progress updates
        :param kwargs: Additional keyword arguments for subprocess
        :returns: subprocess.CompletedProcess object
        """
        import threading
        import time
        
        cmd = [self._ffmpeg_path] + args
        
        # Add threading if specified
        if self._max_threads > 0:
            cmd.extend(["-threads", str(self._max_threads)])
        
        # Add progress reporting
        cmd.extend(["-progress", "pipe:2"])
        
        self._logger.debug("Executing FFmpeg command with progress: %s" % " ".join(cmd))
        
        try:
            # Start process with pipes
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                **kwargs
            )
            
            # Monitor progress in separate thread
            def monitor_progress():
                if process.stderr:
                    while process.poll() is None:
                        try:
                            # Read stderr for progress info
                            line = process.stderr.readline()
                            if line and progress_callback:
                                # Parse FFmpeg progress output
                                if "time=" in line:
                                    # Extract time information for progress
                                    progress_callback(f"FFmpeg: {line.strip()}")
                            
                            # Keep UI responsive
                            time.sleep(0.1)
                        except Exception:
                            break
            
            # Start monitoring thread
            if progress_callback:
                monitor_thread = threading.Thread(target=monitor_progress, daemon=True)
                monitor_thread.start()
            
            # Wait for completion while processing events
            while process.poll() is None:
                # Keep UI responsive - simple approach
                time.sleep(0.1)
            
            # Get final output
            stdout, stderr = process.communicate()
            
            # Create result object similar to subprocess.run
            class ProcessResult:
                def __init__(self, returncode, stdout, stderr):
                    self.returncode = returncode
                    self.stdout = stdout
                    self.stderr = stderr
                    
            result = ProcessResult(process.returncode, stdout, stderr)
            
            if result.returncode != 0:
                self._logger.error("FFmpeg command failed with return code %s" % result.returncode)
                if result.stderr:
                    self._logger.error("FFmpeg stderr: %s" % result.stderr)
            
            return result
            
        except Exception as e:
            self._logger.error("FFmpeg command failed: %s" % str(e))
            raise
    
    def execute_ffprobe_command(self, args, **kwargs):
        """
        Execute FFprobe command with given arguments
        
        :param args: List of arguments to pass to FFprobe
        :param kwargs: Additional keyword arguments for subprocess
        :returns: subprocess.CompletedProcess object
        """
        cmd = [self._ffprobe_path] + args
        
        self._logger.debug("Executing FFprobe command: %s" % " ".join(cmd))
        
        try:
            result = subprocess.run(cmd, **kwargs)
            if result.returncode != 0:
                self._logger.error("FFprobe command failed with return code %s" % result.returncode)
                if hasattr(result, 'stderr') and result.stderr:
                    self._logger.error("FFprobe stderr: %s" % result.stderr)
            return result
        except Exception as e:
            self._logger.error("FFprobe command failed: %s" % str(e))
            raise
    
    # Legacy method for backward compatibility
    def execute_command(self, args, **kwargs):
        """
        Execute FFmpeg command (legacy method)
        
        :param args: List of arguments to pass to FFmpeg
        :param kwargs: Additional keyword arguments for subprocess
        :returns: subprocess.CompletedProcess object
        """
        return self.execute_ffmpeg_command(args, **kwargs)
    
    def get_video_info(self, video_path):
        """
        Get detailed information about a video file using ffprobe
        
        :param video_path: Path to video file
        :returns: Dictionary with video information
        """
        if not os.path.exists(video_path):
            raise ValueError("Video file does not exist: %s" % video_path)
        
        # Use ffprobe for detailed info
        args = [
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
        ]
        
        try:
            result = self.execute_ffprobe_command(args, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            # Extract relevant information
            info = {
                'duration': 0.0,
                'width': None,
                'height': None,
                'fps': None,
                'video_codec': None,
                'audio_codec': None,
                'bitrate': 0,
                'file_size': 0
            }
            
            # Get format info
            if 'format' in data:
                format_info = data['format']
                info['duration'] = float(format_info.get('duration', 0))
                info['bitrate'] = int(format_info.get('bit_rate', 0))
                info['file_size'] = int(format_info.get('size', 0))
            
            # Get stream info
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    info['width'] = stream.get('width')
                    info['height'] = stream.get('height')
                    info['video_codec'] = stream.get('codec_name')
                    
                    # Calculate FPS from rational number
                    fps_str = stream.get('r_frame_rate', '0/1')
                    if '/' in fps_str:
                        num, den = fps_str.split('/')
                        if int(den) != 0:
                            info['fps'] = round(float(num) / float(den), 2)
                
                elif stream.get('codec_type') == 'audio':
                    info['audio_codec'] = stream.get('codec_name')
            
            return info
            
        except subprocess.CalledProcessError as e:
            self._logger.error("ffprobe command failed: %s" % str(e))
            raise
        except json.JSONDecodeError as e:
            self._logger.error("Failed to parse ffprobe output: %s" % str(e))
            raise
    
    def convert_video(self, input_path, output_path, progress_callback=None, **options):
        """
        Convert video file with specified options
        
        :param input_path: Path to input video file
        :param output_path: Path to output video file
        :param progress_callback: Function to call with progress updates
        :param options: FFmpeg options as keyword arguments
                       Examples: vcodec='libx264', acodec='aac', crf=23, preset='medium'
        :returns: subprocess.CompletedProcess object
        """
        if not os.path.exists(input_path):
            raise ValueError("Input file does not exist: %s" % input_path)
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        args = ["-i", input_path]
        
        # Add video codec (use framework setting if not specified)
        try:
            default_video_codec = self._framework.settings.get('default_video_codec', 'libx264')
        except (AttributeError, KeyError):
            default_video_codec = 'libx264'
        
        vcodec = options.pop('vcodec', default_video_codec)
        if vcodec:
            args.extend(["-vcodec", vcodec])
        
        # Add audio codec (use framework setting if not specified)
        try:
            default_audio_codec = self._framework.settings.get('default_audio_codec', 'aac')
        except (AttributeError, KeyError):
            default_audio_codec = 'aac'
            
        acodec = options.pop('acodec', default_audio_codec)
        if acodec:
            args.extend(["-acodec", acodec])
        
        # Add other options
        for key, value in options.items():
            if value is not None:
                args.extend(["-" + key, str(value)])
        
        # Overwrite output file if it exists
        args.append("-y")
        args.append(output_path)
        
        # Use non-blocking execution if progress callback provided
        if progress_callback:
            return self.execute_ffmpeg_with_progress(args, progress_callback=progress_callback)
        else:
            return self.execute_ffmpeg_command(args, capture_output=True, text=True)
    
    def get_media_formats(self):
        """
        Get list of supported formats from FFmpeg
        
        :returns: Dictionary with encoder and decoder format lists
        """
        formats = {'encoders': [], 'decoders': []}
        
        try:
            # Get encoders
            result = self.execute_ffmpeg_command(["-encoders"], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                in_encoders = False
                for line in lines:
                    if line.strip().startswith('------'):
                        in_encoders = True
                        continue
                    if in_encoders and line.strip():
                        # Parse encoder line (format: " V..... libx264")
                        parts = line.split()
                        if len(parts) >= 2:
                            formats['encoders'].append(parts[1])
            
            # Get decoders
            result = self.execute_ffmpeg_command(["-decoders"], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                in_decoders = False
                for line in lines:
                    if line.strip().startswith('------'):
                        in_decoders = True
                        continue
                    if in_decoders and line.strip():
                        parts = line.split()
                        if len(parts) >= 2:
                            formats['decoders'].append(parts[1])
                            
        except Exception as e:
            self._logger.error("Failed to get format information: %s" % str(e))
        
        return formats
    
    def validate_media_file(self, media_path):
        """
        Validate that a media file can be read by FFmpeg/FFprobe
        
        :param media_path: Path to media file
        :returns: Boolean indicating if file is valid
        """
        try:
            args = [
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                media_path
            ]
            
            result = self.execute_ffprobe_command(args, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception:
            return False
    
    def get_stream_info(self, media_path, stream_type=None):
        """
        Get detailed stream information using FFprobe
        
        :param media_path: Path to media file
        :param stream_type: Filter by stream type ('video', 'audio', 'subtitle') or None for all
        :returns: List of stream dictionaries
        """
        if not os.path.exists(media_path):
            raise ValueError("Media file does not exist: %s" % media_path)
        
        args = [
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams"
        ]
        
        if stream_type:
            args.extend(["-select_streams", stream_type[0]])  # 'v' for video, 'a' for audio, etc.
        
        args.append(media_path)
        
        try:
            result = self.execute_ffprobe_command(args, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            return data.get('streams', [])
            
        except subprocess.CalledProcessError as e:
            self._logger.error("ffprobe command failed: %s" % str(e))
            raise
        except json.JSONDecodeError as e:
            self._logger.error("Failed to parse ffprobe output: %s" % str(e))
            raise
    
    def extract_frames(self, video_path, output_pattern, start_time=None, duration=None, fps=None):
        """
        Extract frames from video
        
        :param video_path: Path to input video
        :param output_pattern: Output pattern (e.g., 'frame_%04d.png')
        :param start_time: Start time in seconds (optional)
        :param duration: Duration in seconds (optional)
        :param fps: Frame rate for extraction (optional)
        :returns: subprocess.CompletedProcess object
        """
        args = []
        
        # Add start time if specified
        if start_time is not None:
            args.extend(["-ss", str(start_time)])
        
        args.extend(["-i", video_path])
        
        # Add duration if specified
        if duration is not None:
            args.extend(["-t", str(duration)])
        
        # Add fps if specified
        if fps is not None:
            args.extend(["-vf", "fps=%s" % fps])
        
        # Overwrite existing files
        args.append("-y")
        args.append(output_pattern)
        
        return self.execute_ffmpeg_command(args, capture_output=True, text=True)
    
    def create_proxy(self, input_path, output_path, resolution="720p", quality="medium"):
        """
        Create a proxy/preview version of a video
        
        :param input_path: Path to input video
        :param output_path: Path to output proxy
        :param resolution: Target resolution ('720p', '1080p', or 'WIDTHxHEIGHT')
        :param quality: Quality preset ('fast', 'medium', 'slow')
        :returns: subprocess.CompletedProcess object
        """
        # Resolution mapping
        resolution_map = {
            '720p': '1280x720',
            '1080p': '1920x1080',
            '480p': '854x480'
        }
        
        target_res = resolution_map.get(resolution, resolution)
        
        # Quality to CRF mapping
        quality_map = {
            'fast': {'crf': '28', 'preset': 'fast'},
            'medium': {'crf': '23', 'preset': 'medium'},
            'slow': {'crf': '18', 'preset': 'slow'}
        }
        
        settings = quality_map.get(quality, quality_map['medium'])
        
        return self.convert_video(
            input_path,
            output_path,
            vf="scale=%s" % target_res,
            crf=settings['crf'],
            preset=settings['preset']
        )
    
    def create_thumbnail(self, video_path, output_path, time_offset="00:00:01"):
        """
        Create a thumbnail image from video at specified time
        
        :param video_path: Path to input video
        :param output_path: Path to output thumbnail
        :param time_offset: Time offset for thumbnail (format: HH:MM:SS or seconds)
        :returns: subprocess.CompletedProcess object
        """
        args = [
            "-i", video_path,
            "-ss", str(time_offset),
            "-vframes", "1",
            "-y",
            output_path
        ]
        
        return self.execute_ffmpeg_command(args, capture_output=True, text=True)