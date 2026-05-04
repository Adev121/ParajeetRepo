# Screen & Audio Assistant

This application provides a transparent screen overlay that uses Google's Gemini API to answer questions visible on your screen or spoken in system audio.

## Prerequisites

1. Python 3.10 or higher.
2. An active Google Gemini API Key.

## Setup

1. Open your terminal or command prompt in this directory (`d:\ParakeetAi`).
2. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Set your Google API key as an environment variable:
   - On Windows Command Prompt:
     ```cmd
     set GOOGLE_API_KEY=your_api_key_here
     ```
   - On Windows PowerShell:
     ```powershell
     $env:GOOGLE_API_KEY="your_api_key_here"
     ```
4. Run the application:
   ```bash
   python main.py
   ```

## How to Use

Once the application is running, you will see a transparent text overlay on the right side of your screen indicating it is ready.

1. **Answer from Screen**: Press `Ctrl+Shift+S`. The app will capture your screen, send it to Gemini, and display the answer on the overlay.
2. **Answer from Audio**: Press `Ctrl+Shift+A`. The app will listen to your system audio (what you hear through your speakers/headphones) for 5 seconds, transcribe it, and ask Gemini for an answer.

> **Note**: For system audio capture to work correctly, ensure your default audio output device supports WASAPI loopback capture (most standard Windows setups do).
