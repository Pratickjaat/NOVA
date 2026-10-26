import subprocess
import webbrowser
from datetime import datetime
from urllib.parse import quote_plus


def open_website(url):
    """Open a website in the default browser."""
    webbrowser.open(url)
    return "Website opened."


def open_application(app_name):
    applications = {
        "notepad": ["notepad.exe"],
        "calculator": ["calc.exe"],
        "paint": ["mspaint.exe"],
        "file explorer": ["explorer.exe"],
    }

    app_name = app_name.lower().strip()

    if app_name not in applications:
        return f"Sorry, I don't support opening {app_name} yet."

    try:
        subprocess.Popen(applications[app_name])
        return f"Opening {app_name}."
    except OSError as error:
        print("Application error:", error)
        return f"I couldn't open {app_name}."


def tell_time():
    current_time = datetime.now().strftime("%I:%M %p")
    return f"It's {current_time}."


def tell_date():
    current_date = datetime.now().strftime("%d %B %Y")
    return f"It's {current_date}."


def search_google(query):
    query = query.strip()

    if not query:
        return "What would you like me to search for?"

    search_url = (
        "https://www.google.com/search?q=" + quote_plus(query)
    )

    webbrowser.open(search_url)
    return f"Searching Google for {query}."
