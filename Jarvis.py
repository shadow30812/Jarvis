# Uses python=3.9.23
# Change length of user response in line 89

import logging
import os
import subprocess
import sys
import time
import webbrowser

import musicLibrary
import pvcobra as cobra
import pvporcupine as porcupine
import pygame
import requests
import speech_recognition as sr
from dotenv import load_dotenv
from gtts import gTTS
from openai import OpenAI
from pvrecorder import PvRecorder

# Load .env file
if load_dotenv():
    # Store keys in variables
    pico_key = os.getenv("PICO")
    pplx_key = os.getenv("PPLX")
    news_key = os.getenv("NEWS")
else:
    print("Something went terribly wrong. Please try later or notify the author.")
    sys.exit(1)

# Initialize Cobra and Porcupine if access key is found; Initialise voice recognizer
if pico_key:
    cobra_handle = cobra.create(access_key=pico_key)
    porcupine_handle = porcupine.create(
        access_key=pico_key,
        keywords=["jarvis"],
        sensitivities=[0.4],  # Default is 0.5, lower is more sensitive
    )
    recorder = PvRecorder(device_index=-1, frame_length=porcupine_handle.frame_length)
recognizer = sr.Recognizer()

logging.basicConfig(
    filename="jarvis.log",  # Log file name
    level=logging.INFO,  # Log INFO and above (WARNING, ERROR, CRITICAL)
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def speak(text):
    logging.info(f"Assistant response: {text}")
    try:
        tts = gTTS(text, lang="en", tld="co.in")
        tts.save("temp.mp3")

        # Initialize Pygame mixer
        pygame.mixer.init()

        # Load the MP3 file
        pygame.mixer.music.load("temp.mp3")

        # Play the MP3 file
        pygame.mixer.music.play()

        # Keep the program running until the music stops playing
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

        # Delete temporary file after program is over
        pygame.mixer.music.unload()
        os.remove("temp.mp3")

    except Exception:
        print(
            "Sorry sir, there was an error in the text-to-speech engine. Your response is being printed from the next line."
        )
        print(text)


def aiProcess(command):
    if not pplx_key:
        return
    client = OpenAI(api_key=pplx_key, base_url="https://api.perplexity.ai")
    response = client.chat.completions.create(
        model="sonar-pro",
        messages=[
            {
                "role": "system",
                "content": "You are a virtual assistant named Jarvis skilled in scientific and computational logic."
                "Please try to keep your responses short and precise, preferably within 100 words."
                "If doing so leaves out a large amount of important information, inform the user in the first line itself.",
            },
            {"role": "user", "content": command},
        ],
    )
    reply = response.choices[0].message.content
    if reply:
        response_text = reply.strip()
        logging.info(f"AI response: {response_text}")
        return response_text
    else:
        return ""


def processCommand(c):
    # Closing cmd takes precedence because accelerator should never overpower the brake in resting position
    if ("close" in c.lower()) or ("exit" in c.lower()):
        os._exit(0)

    # Opening apps
    elif "code" in c.lower():
        subprocess.run(
            [r"C:\Users\LENOVO\AppData\Local\Programs\Microsoft VS Code\Code.exe"]
        )
    elif ("info" in c.lower()) or ("plot" in c.lower()):
        subprocess.run(
            [r"C:\Users\LENOVO\AppData\Local\Programs\Perplexity\Perplexity.exe"]
        )
    elif "discord" in c.lower():
        subprocess.run(
            [r"C:\Users\LENOVO\AppData\Local\Discord\app-1.0.9191\Discord.exe"]
        )
    elif ("message" in c.lower()) or ("whatsapp" in c.lower()):
        subprocess.run([r"start Whatsapp:"])

    # Opening websites
    elif "note" in c.lower():
        webbrowser.open("https://keep.google.com/u/0/")
    elif ("search" in c.lower()) or ("google" in c.lower()):
        webbrowser.open("https://www.google.com")
    elif "youtube" in c.lower():
        webbrowser.open("https://www.youtube.com")

    # Play some music man
    elif c.lower().startswith("play"):
        command_parts = c.lower().split(" ")
        if len(command_parts) < 2:
            return
        song = " ".join(command_parts[1:])  # Get all words after "play"
        link = musicLibrary.music[song]
        if link:
            webbrowser.open(link)
        else:
            speak(f"Sorry sir, I couldn't find {song} in the library.")

    # Listen to the news
    elif "news" in c.lower():
        if not news_key:
            return
        r = requests.get(
            f"https://newsapi.org/v2/top-headlines?country=in&apiKey={news_key}"
        )
        if r.status_code == 200:
            # Parse the JSON response
            data = r.json()

            # Extract the articles
            articles = data.get("articles", [])

            # Print the headlines
            for article in articles:
                speak(article["title"])

    # Uncomment the following lines and comment the corresponding lines in the upper elif block if there are issues with working code
    # url = (f'https://newsapi.org/v2/top-headlines?'
    #        'country=us&'
    #        'apiKey={news_key}')
    # response = requests.get(url)
    # print response.json()

    else:
        # Let OpenAI handle the request
        speak(
            "Sir, the query does not match any native files or programs. I'm now searching the web."
        )
        try:
            output = aiProcess(c)
            speak(output)
        except Exception:
            speak(
                "I'm sorry sir, the servers seem to be busy at the moment. Please try again after sometime."
            )


def handle_command():
    speak("I'm here sir")
    # Listen for command
    with sr.Microphone() as source:
        print("Jarvis Active...")
        audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
        try:
            command = recognizer.recognize_google(audio)
            logging.info(f"User command: {command}")
            print(command)
            processCommand(command)
        except Exception as e:
            print(f"Error recognizing command: {e}")


def main_loop():
    recorder.start()
    try:
        print("Calibrating microphone...")
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(
                source, duration=3
            )  # Adjust for ambient noise for 3-5s
            recognizer.dynamic_energy_threshold = (
                True  # To change the threshold based on changing environments
            )
            print(
                f"Energy threshold set to: {recognizer.energy_threshold}"
            )  # Higher threshold is for noisy environments
        print("Listening...")
        while True:
            pcm = recorder.read()

            # Step 1: Use Cobra to check if speech is present
            voice_probability = cobra_handle.process(pcm)
            if (
                voice_probability < 0.5
            ):  # Adjust threshold as needed (higher probability means threshold increases to louder speech)
                continue  # Skip Porcupine if no speech

            # Step 2: Only check for wake word when speech is detected
            keyword_index = porcupine_handle.process(pcm)
            if keyword_index >= 0:
                time.sleep(0.5)
                print("Wake word detected!")
                handle_command()  # Existing command logic

    except KeyboardInterrupt:
        print("Exiting...")

    finally:
        recorder.stop()
        recorder.delete()
        cobra_handle.delete()
        porcupine_handle.delete()


if __name__ == "__main__":
    main_loop()
