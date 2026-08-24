# neuromentor-v2-app

This application functions as an asynchronous web interface designed to facilitate interactive educational sessions using LLM-based guidance. It utilizes a persistent storage layer to track user progress and conversation history, allowing the system to maintain context across multiple interaction sessions.

### How it works

The system is structured around an asynchronous event loop that manages concurrent requests from both the Telegram API and the web frontend.

#### Telegram Bot Component
The bot uses the python-telegram-bot library to poll for updates. When a user sends a message, the bot processes the input, potentially triggers speech-to-text conversion if audio is provided, and forwards the context to the OpenAI API. The resulting response is then stored in the database and returned to the user.

#### Web Interface
The web component is built on the Quart framework, providing an asynchronous interface for administrative tasks and session monitoring. It shares the same database schema as the bot, ensuring that state remains consistent regardless of the entry point.

#### Data Persistence
The application uses SQLAlchemy and Tortoise-ORM to handle database interactions. All conversation history and user states are persisted in a relational database, which allows for long-term memory of educational sessions. The system relies on asynchronous database drivers to prevent blocking the event loop during I/O operations.

### Tech Stack

- Quart (Asynchronous web framework)
- python-telegram-bot (Telegram API wrapper)
- OpenAI API (LLM integration)
- SQLAlchemy / Tortoise-ORM (Database ORM)
- asyncpg (PostgreSQL driver)
- Pydub / SpeechRecognition (Audio processing)

### Running locally

1. Clone the repository and set up a virtual environment:
   python -m venv venv
   source venv/bin/activate

2. Install the dependencies:
   pip install -r requirements.txt

3. Create a .env file based on .env.example and populate the required variables:
   DATABASE_URL=your_database_url
   OPENAI_API_KEY=your_openai_key
   PORT=5000

4. Start the application:
   python site/app.py
