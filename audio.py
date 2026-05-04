import pyaudiowpatch as pyaudio
import wave
import speech_recognition as sr
import os

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
