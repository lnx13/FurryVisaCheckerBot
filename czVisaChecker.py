#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'AinonLynx'

import sqlite3

from selenium import webdriver
from selenium.webdriver.support.ui import Select
import telegram


class VisaChecker():
    validCities = ["Kiev", "Lviv", "Odessa", "Dnipropetrovsk", "Uzhgorod"]

    def __init__(self, token, db="visaChecker.db"):
        """Init telegram bot and sqlite database"""
        self.browser = webdriver.Firefox()
        self.results = {}
        self.bot = telegram.Bot(token=token)
        self.conn = sqlite3.connect(db)
        c = self.conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, chatId, city, lastState, UNIQUE(chatId, city))")
        self.conn.commit()

    def send_doge(self, chatId):
        """Doge easter egg"""
        # self.bot.sendPhoto(chat_id=chatId,photo='https://upload.wikimedia.org/wikipedia/ru/5/5f/Original_Doge_meme.jpg')
        self.bot.sendSticker(chat_id=chatId,sticker='BQADAgAD3gAD9HsZAAFphGBFqImfGAI')
        self.bot.sendMessage(chat_id=chatId, text="Such doge, so wow, many visas!")

    def message_parse(self, msg, chatId):
        """Parse received message and execute command"""
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
            self.send_doge(chatId)

        elif "/track" in msg:
            try:
                ref_num = msg.split(" ")[1]
                birthday = msg.split(" ")[2]
            except IndexError:
                self.bot.sendMessage(chat_id=chatId, text="Example: /track refNumber birthday_dd/mm/yyyy")
                return

            code, message = self.track_visa(ref_num, birthday)
            if code == 0:
                self.bot.sendMessage(chat_id=chatId, text=message)
            else:
                self.bot.sendMessage(chat_id=chatId, text="Track error :(")

    def get_messages(self):
        """Get all bot messages"""
        updates = self.bot.getUpdates()
        try:
            last_update_id = updates[-1].update_id
        except IndexError:
            last_update_id = 0
        self.bot.getUpdates(offset=(last_update_id+1)) # make all messages read
        print "last update id: " + str(last_update_id)
        for u in updates:
            self.message_parse(u.message.text, u.message.chat_id)
        print "updates checked"
        print [u.message.text for u in updates]

    def track_visa(self, ref_number, birthday):
        """Track visa application status"""
        try:
            self.browser.get('https://www.vfsvisaonline.com/czech-onlinetracking/')
            assert 'Tracking' in self.browser.title
            self.browser.implicitly_wait(2)
            self.browser.find_element_by_id('ContentMain_txtgwfNumber').send_keys(ref_number)
            self.browser.find_element_by_id('ContentMain_txtDOB').send_keys(birthday)
            self.browser.implicitly_wait(2)
            self.browser.find_element_by_id('ContentMain_btnSubmit').click()
            self.browser.implicitly_wait(2)
            text = self.browser.find_element_by_id('ContentMain_lblTrackingMessage').text
            print text.encode("UTF-8")
            try:
                eng_text = text.split("\n")[0]  # get english message
            except IndexError:
                eng_text = "String split error, try again"

            msg = "Ref number: " + ref_number + "\n" + eng_text
            return (0, msg)
        except Exception, e:
            # browser.save_screenshot('screen.png')
            print e
            return (-1, str(e))


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
            self.browser.get('http://www.vfsglobal.com/czechrepublic/ukraine/english/Schedule_an_appointment.html')
            assert 'Visa' in self.browser.title

            iframe = self.browser.find_elements_by_tag_name('iframe')[0]
            self.browser.switch_to_frame(iframe)
            self.browser.implicitly_wait(2)
            self.browser.find_element_by_link_text('Schedule Appointment').click()

            Select(self.browser.find_element_by_id('ctl00_plhMain_cboVAC')).select_by_visible_text(city)
            self.browser.find_element_by_id('ctl00_plhMain_btnSubmit').click()
            self.browser.implicitly_wait(2)
            Select(self.browser.find_element_by_id('ctl00_plhMain_cboVisaCategory')).select_by_visible_text('Tourism')
            self.browser.implicitly_wait(2)
            ps = self.browser.page_source
            text = self.browser.find_element_by_id('ctl00_plhMain_lblMsg').text
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
    check.browser.quit()

main()
