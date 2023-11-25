# How to start

1. `git clone https://github.com/ceo-s/kia_bot.git`
2. `cd kia_bot`
3. `pip install -r requirements.txt`
4. Create .env file with following variables:
   1. `OPENAI_API_KEY`
   2. `BOT_TOKEN`
   3. `LOGGING_BOT_TOKEN`
   4. `LOGGING_END_USERS`
5. `python setup.py`
6. Copy all text documents for embedding indexing to db/text
7. `python main.py`
