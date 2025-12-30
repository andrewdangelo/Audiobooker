"""
Alternative audio processor using soundfile and numpy
More reliable on Windows systems
"""
import soundfile as sf
import numpy as np
from pathlib import Path
from typing import Optional, Tuple
import os
import subprocess
import json

class AudioProcessor:
    """Utility class for audio file processing using soundfile"""
    
    @staticmethod
    def get_audio_metadata(file_path: str) -> dict:
        """
        Extract metadata from audio file using ffprobe
        
        Returns:
            dict with duration_seconds, format, sample_rate, channels, file_size_bytes
        """
        try:
            #TODO : RUN apt-get update && apt-get install -y ffmpeg in dockerfile onto the VM
            # Use ffprobe to get metadata
            cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', file_path]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            data = json.loads(result.stdout)
            audio_stream = next((s for s in data.get('streams', []) if s['codec_type'] == 'audio'), {})
            
            format_info = data.get('format', {})
            file_size = os.path.getsize(file_path)
            
            return {
                "duration_seconds": float(format_info.get('duration', 0)),
                "format": Path(file_path).suffix[1:],
                "sample_rate": int(audio_stream.get('sample_rate', 44100)),
                "channels": int(audio_stream.get('channels', 2)),
                "bitrate": format_info.get('bit_rate'),
                "file_size_bytes": file_size
            }
        except Exception as e:
            raise ValueError(f"Failed to read audio metadata: {str(e)}")
    
    @staticmethod
    def validate_audio_file(file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if audio file exists and is readable
        
        Returns:
            (is_valid, error_message)
        """
        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}"
        
        if not os.path.isfile(file_path):
            return False, f"Path is not a file: {file_path}"
        
        # Try to read the audio
        try:
            info = sf.info(file_path)
            return True, None
        except Exception as e:
            return False, f"Invalid audio file: {str(e)}"
    
    @staticmethod
    def load_audio(file_path: str) -> Tuple[np.ndarray, int]:
        """
        Load audio file
        Returns: (audio_data, sample_rate)
        """
        data, samplerate = sf.read(file_path)
        return data, samplerate
    
    @staticmethod
    def normalize_audio_levels(audio: np.ndarray) -> np.ndarray:
        """Normalize audio volume to -3dB peak"""
        max_val = np.abs(audio).max()
        if max_val > 0:
            # Normalize to 0.707 (-3dB) to avoid clipping
            return audio * (0.707 / max_val)
        return audio
    
    @staticmethod
    def apply_crossfade(audio1: np.ndarray, audio2: np.ndarray, crossfade_samples: int, sample_rate: int) -> np.ndarray:
        """
        Apply crossfade between two audio arrays
        
        Args:
            audio1: First audio array
            audio2: Second audio array
            crossfade_samples: Number of samples for crossfade
            sample_rate: Sample rate
            
        Returns:
            Combined audio with crossfade
        """
        if crossfade_samples <= 0:
            return np.concatenate([audio1, audio2])
        
        # Ensure both arrays have same number of channels
        if audio1.ndim != audio2.ndim:
            if audio1.ndim == 1:
                audio1 = np.expand_dims(audio1, axis=1)
            if audio2.ndim == 1:
                audio2 = np.expand_dims(audio2, axis=1)
        
        # Make sure crossfade doesn't exceed audio length
        max_crossfade = min(len(audio1), len(audio2), crossfade_samples)
        
        if max_crossfade <= 0:
            return np.concatenate([audio1, audio2])
        
        # Create fade curves
        fade_out = np.linspace(1, 0, max_crossfade)
        fade_in = np.linspace(0, 1, max_crossfade)
        
        # Handle multi-channel audio
        if audio1.ndim > 1:
            fade_out = fade_out.reshape(-1, 1)
            fade_in = fade_in.reshape(-1, 1)
        
        # Apply crossfade
        end_of_first = audio1[-max_crossfade:]
        start_of_second = audio2[:max_crossfade]
        
        crossfaded = end_of_first * fade_out + start_of_second * fade_in
        
        # Combine: first audio (minus crossfade) + crossfaded section + rest of second audio
        result = np.concatenate([audio1[:-max_crossfade], crossfaded, audio2[max_crossfade:]])
        
        return result
    
    @staticmethod
    def concatenate_audio_segments(file_paths: list[str], crossfade_ms: int = 0, normalize_levels: bool = True) -> Tuple[np.ndarray, int]:
        """
        Concatenate multiple audio files
        
        Args:
            file_paths: List of audio file paths
            crossfade_ms: Crossfade duration in milliseconds
            normalize_levels: Whether to normalize volume levels
            
        Returns:
            (combined_audio, sample_rate)
        """
        if not file_paths:
            raise ValueError("No audio files to concatenate")
        
        # Load first file to get sample rate
        first_audio, sample_rate = AudioProcessor.load_audio(file_paths[0])
        
        # Load all audio files
        audio_segments = [first_audio]
        for file_path in file_paths[1:]:
            audio, sr = AudioProcessor.load_audio(file_path)
            
            # Resample if necessary (basic resampling)
            if sr != sample_rate:
                # Use ffmpeg for resampling or skip for now
                raise ValueError(f"Sample rate mismatch: {sr} vs {sample_rate}")
            
            audio_segments.append(audio)
        
        # Normalize each segment if requested
        if normalize_levels:
            audio_segments = [AudioProcessor.normalize_audio_levels(seg) for seg in audio_segments]
        
        # Calculate crossfade in samples
        crossfade_samples = int(crossfade_ms * sample_rate / 1000)
        
        # Start with first segment
        result = audio_segments[0]
        
        # Add remaining segments with crossfade
        for segment in audio_segments[1:]:
            result = AudioProcessor.apply_crossfade(result, segment, crossfade_samples, sample_rate)
        
        return result, sample_rate
    
    @staticmethod
    def export_audio(audio: np.ndarray, output_path: str, sample_rate: int, format: str = "mp3", bitrate: str = "128k") -> str:
        """
        Export audio to file using ffmpeg
        
        Returns:
            Path to exported file
        """
        # First save as WAV temporarily
        temp_wav = output_path.replace(f'.{format}', '_temp.wav')
        sf.write(temp_wav, audio, sample_rate)
        
        # Convert to desired format with ffmpeg
        if format != 'wav':
            cmd = ['ffmpeg', '-i', temp_wav, '-b:a', bitrate, '-y', output_path]
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Remove temp file
            os.remove(temp_wav)
        else:
            # Just rename if WAV
            os.rename(temp_wav, output_path)
        
        return output_path
    
    @staticmethod
    def get_audio_chunk_bytes(audio: np.ndarray, sample_rate: int, chunk_size: int = 4096, format: str = "mp3", bitrate: str = "128k"):
        """
        Generator that yields audio data in chunks
        Useful for streaming
        
        Args:
            audio: Audio array to stream
            sample_rate: Sample rate
            chunk_size: Size of each chunk in bytes
            format: Export format
            bitrate: Audio bitrate
            
        Yields:
            Bytes of audio data
        """
        import io
        import tempfile
        
        # Export to temporary file
        with tempfile.NamedTemporaryFile(suffix=f'.{format}', delete=False) as tmp:
            temp_path = tmp.name
        
        try:
            AudioProcessor.export_audio(audio, temp_path, sample_rate, format, bitrate)
            
            # Read and yield chunks
            with open(temp_path, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        finally:
            # Cleanup temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)