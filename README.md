FurryVisaCheckerBot
===================

Бот для telegram, проверяет наличие свободных мест в визовых центрах Чехии в Укрине.
Доступен под именем @FurryVisaCheckerBot. Общается как лично так и в груповых чатах.

Зависимости
-----------
* Selenium -- pip install selenium
* leandrotoledo/python-telegram-bot -- pip install python-telegram-bot
* firefox -- apt-get install firefox
* Xvfb -- apt-get install xvfb. Нужен для запуска в фоне

Использование
-------------
`xvfb-run ./czVisaChecker.py`

Скрипт запускается по cron, при каждом запуске обрабатывает все полученые сообщения и если имеются активные подписки выполняет проверки наличия свободных мест.

