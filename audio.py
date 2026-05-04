import pyaudiowpatch as pyaudio
import wave
import speech_recognition as sr
import os
import struct
import math


def _rms(data: bytes) -> float:
    """Calculate RMS amplitude of a raw PCM Int16 chunk."""
    count = len(data) // 2
    if count == 0:
        return 0.0
    shorts = struct.unpack(f"{count}h", data)
    return math.sqrt(sum(s * s for s in shorts) / count)


def listen_continuously(on_segment, stop_event,
                        silence_threshold: int = 500,
                        silence_duration: float = 1.2,
                        min_speech_duration: float = 0.4):
    """
    Continuously record system loopback audio.
    Whenever a speech segment ends (pause >= silence_duration seconds),
    saves it to a temp wav and calls on_segment(wav_path).
    Stops cleanly when stop_event is set.
    """
    CHUNK = 512
    FORMAT = pyaudio.paInt16

    p = pyaudio.PyAudio()
    try:
        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
        if not default_speakers["isLoopbackDevice"]:
            for loopback in p.get_loopback_device_info_generator():
                if default_speakers["name"] in loopback["name"]:
                    default_speakers = loopback
                    break
            else:
                return

        rate = int(default_speakers["defaultSampleRate"])
        channels = default_speakers["maxInputChannels"]

        stream = p.open(
            format=FORMAT,
            channels=channels,
            rate=rate,
            frames_per_buffer=CHUNK,
            input=True,
            input_device_index=default_speakers["index"],
        )

        frames = []
        silent_chunks = 0
        speech_chunks = 0
        silence_limit   = int(rate / CHUNK * silence_duration)
        min_speech_limit = int(rate / CHUNK * min_speech_duration)
        in_speech = False

        while not stop_event.is_set():
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
            except Exception:
                break

            if _rms(data) > silence_threshold:
                # --- speech ---
                in_speech = True
                frames.append(data)
                speech_chunks += 1
                silent_chunks = 0
            else:
                # --- silence ---
                if in_speech:
                    silent_chunks += 1
                    frames.append(data)          # keep trailing silence for natural audio
                    if silent_chunks >= silence_limit:
                        if speech_chunks >= min_speech_limit:
                            tmp = "segment_audio.wav"
                            wf = wave.open(tmp, "wb")
                            wf.setnchannels(channels)
                            wf.setsampwidth(p.get_sample_size(FORMAT))
                            wf.setframerate(rate)
                            wf.writeframes(b"".join(frames))
                            wf.close()
                            on_segment(tmp)
                        frames = []
                        speech_chunks = 0
                        silent_chunks = 0
                        in_speech = False

        stream.stop_stream()
        stream.close()
    except Exception as e:
        print(f"Continuous audio error: {e}")
    finally:
        p.terminate()


def record_system_audio(duration=5, output_filename="system_audio.wav"):
    """Records system loopback audio (what you hear) for a given duration."""
    CHUNK = 512
    FORMAT = pyaudio.paInt16
    
    p = pyaudio.PyAudio()
    
    try:
        # Get default WASAPI info
        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
        
        if not default_speakers["isLoopbackDevice"]:
            for loopback in p.get_loopback_device_info_generator():
                if default_speakers["name"] in loopback["name"]:
                    default_speakers = loopback
                    break
            else:
                return None

        stream = p.open(format=FORMAT,
                channels=default_speakers["maxInputChannels"],
                rate=int(default_speakers["defaultSampleRate"]),
                frames_per_buffer=CHUNK,
                input=True,
                input_device_index=default_speakers["index"])

        frames = []
        for i in range(0, int(int(default_speakers["defaultSampleRate"]) / CHUNK * duration)):
            data = stream.read(CHUNK)
            frames.append(data)

        stream.stop_stream()
        stream.close()
        p.terminate()

        wf = wave.open(output_filename, 'wb')
        wf.setnchannels(default_speakers["maxInputChannels"])
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(int(default_speakers["defaultSampleRate"]))
        wf.writeframes(b''.join(frames))
        wf.close()
        
        return output_filename
    except Exception as e:
        print(f"Audio record error: {e}")
        return None

def transcribe_audio(filename):
    """Transcribes an audio file using SpeechRecognition."""
    if not filename or not os.path.exists(filename):
        return "Audio file not found."
        
    r = sr.Recognizer()
    try:
        with sr.AudioFile(filename) as source:
            audio_data = r.record(source)
            # Using Google's free web API for simplicity. 
            # For privacy/offline, use whisper: model = whisper.load_model("base"); result = model.transcribe(filename)
            text = r.recognize_google(audio_data)
            return text
    except sr.UnknownValueError:
        return "" # Nothing understood
    except sr.RequestError as e:
        return f"[Audio API Error: {e}]"
    except Exception as e:
        return f"[Transcription error: {e}]"
