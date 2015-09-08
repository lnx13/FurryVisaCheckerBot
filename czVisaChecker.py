#!/usr/bin/env python
__author__ = 'AinonLynx'

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import telegram
import sqlite3


class VisaChecker():
    validCities = ["Kiev", "Lviv", "Odessa", "Dnipropetrovsk", "Uzhgorod"]

    def __init__(self, token, db="visaChecker.db"):
        """Init telegram bot and sqlite database"""
        self.results = {}
        self.bot = telegram.Bot(token=token)
        self.conn = sqlite3.connect(db)
        c = self.conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, chatId, city, lastState, UNIQUE(chatId, city))")
        self.conn.commit()

    def sendDoge(self, chatId):
        """Doge easter egg"""
        self.bot.sendPhoto(chat_id=chatId,photo='https://upload.wikimedia.org/wikipedia/ru/5/5f/Original_Doge_meme.jpg')
        self.bot.sendMessage(chat_id=chatId, text="Such doge, so wow, many visas!")

    def message_parse(self, msg, chatId):
        """Parce received message and execute command"""
        c = self.conn.cursor()

        if "/subscribe" in msg:
            try:
                city = msg.split(" ")[1]
            except IndexError:
                city = "Kiev"
            if city not in self.validCities:
                self.bot.sendMessage(chat_id=chatId, text="Invalid city name, use Kiev")
                city = "Kiev"
            try:
                c.execute("INSERT INTO chats (chatId, city) VALUES(?,?)", [chatId, city])
                self.conn.commit()
                self.bot.sendMessage(chat_id=chatId, text="Subscribed to " + city)
            except:
                self.bot.sendMessage(chat_id=chatId, text="Already subscribed to " + city)

        elif "/unsubscribe" in msg:
            try:
                c.execute("DELETE FROM chats WHERE chatId=?", (chatId,))
                self.conn.commit()
                self.bot.sendMessage(chat_id=chatId, text="Unsubscribed from all")
            except:
                self.bot.sendMessage(chat_id=chatId, text="command error :(")
            pass
        elif "/status" in msg:
            # !there are some problems with city variable
            msgL = msg.split(" ")
            if len(msgL) > 1:
                city = msg.split(" ")[1]
                if city in self.validCities:
                    code, message = self.check_visa(city=city)
                    if code == 0:
                        self.bot.sendMessage(chat_id=chatId, text=message)
                else:
                    self.bot.sendMessage(chat_id=chatId, text="Invalid city " + city)
            else:
                cities = c.execute("SELECT city from chats WHERE chatId=?", (chatId,)).fetchall()
                if len(cities) > 0:
                    for city in cities:
                        code, message = self.check_visa(city=city[0])
                        if code == 0:
                            self.bot.sendMessage(chat_id=chatId, text=message)
                            c.execute("UPDATE chats SET lastState=? WHERE chatId=? AND city=?", (message, chatId, city[0]))
                    self.conn.commit()
                else:
                    code, message = self.check_visa(city="Kiev")
                    if code == 0:
                       self.bot.sendMessage(chat_id=chatId, text=message)
        elif "wow" in msg:
            self.sendDoge(chatId)


    def get_messages(self):
        """Get all bot messages"""
        updates = self.bot.getUpdates()
        try:
            lastUpdateId = updates[-1].update_id
        except IndexError:
            lastUpdateId = 0
        self.bot.getUpdates(offset=(lastUpdateId+1)) # make all messages read
        print "last update id: " + str(lastUpdateId)
        for u in updates:
            self.message_parse(u.message.text, u.message.chat_id)
        print "updates checked"
        print [u.message.text for u in updates]

    def check_visa(self, city):
        """Checks free slots in visa application center
        return tuple (retCode, message)
        retCode: 0 -- ok, -1 -- error
        """ 
        if city not in self.validCities:
            return (-1, "Unknown city")
        if city in self.results:
            return self.results[city]

        try:
            browser = webdriver.Firefox()
            browser.get('http://www.vfsglobal.com/czechrepublic/ukraine/english/Schedule_an_appointment.html')
            assert 'Visa' in browser.title

            iframe = browser.find_elements_by_tag_name('iframe')[0]
            browser.switch_to_frame(iframe)
            browser.implicitly_wait(2)
            browser.find_element_by_link_text('Schedule Appointment').click()

            Select(browser.find_element_by_id('ctl00_plhMain_cboVAC')).select_by_visible_text(city)
            browser.find_element_by_id('ctl00_plhMain_btnSubmit').click()
            browser.implicitly_wait(2)
            Select(browser.find_element_by_id('ctl00_plhMain_cboVisaCategory')).select_by_visible_text('Tourism')
            browser.implicitly_wait(2)
            ps = browser.page_source
            text = browser.find_element_by_id('ctl00_plhMain_lblMsg').text
            browser.quit()
            if "No date" in ps:
                res = (0, "No dates in " + city)
                self.results[city] = res
                return res
            else:
                msg = "yay^__^ Free slots found in " + city + '\n'
                msg += text
                res = (0, msg)
                self.results[city] = res
                return res

        except Exception, e:
            # browser.save_screenshot('screen.png')
            print e
            try:
                browser.quit()
            except:
                pass
            return (-1, str(e))


def main():
    check = VisaChecker("API_TOKEN")
    check.get_messages() # processing received massages

    # processing subscriptions
    c = check.conn.cursor() 
    for chatId, city, lastState in c.execute("SELECT chatId, city, lastState FROM chats").fetchall():
        code, msg = check.check_visa(city)
        if code == 0:
            if msg != lastState:
                check.bot.sendMessage(chat_id=chatId, text=msg)
                c.execute("UPDATE chats SET lastState=? WHERE city=? AND chatId=?", (msg, city, chatId))
                check.conn.commit()
    check.conn.close()

main()
