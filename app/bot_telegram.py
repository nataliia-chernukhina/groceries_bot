# telegram bot classes

import uuid
from telegram.ext import Updater
from telegram import Update, Bot, ForceReply
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from collections import defaultdict
from enum import IntEnum
import json
import logging


BOT_TOKEN = '1579751582:AAEcot5v5NLyxXB1uFYQiBCyvBAsKOzGGsU'
CHAIN_LIST = ['waitrose', 'tesco', 'coop', 'asda', 'lidl', 'sainsbury']


class CredMode(IntEnum):
    login = 0
    pwd = 1
    login_pwd = 2


class BotState:
    def __init__(self):
        self.chain_name = None
        self.last_message = None
        self.state_list = []

        self.login = None
        self.password = None
        self._cvv = None

    @property
    def cvv(self):
        return self._cvv

    @cvv.setter
    def cvv(self, value: int):
        if value and (not int(value) or len(str(value)) != 3):
            raise ValueError(f'Invalid cvv {value}, must be 3 digit number!')
        self._cvv = value

    def get_creds(self, chat_id: int):
        with open('creds.json') as json_file:
            data = json.load(json_file)
        return data.get(str(chat_id), {}).get(self.chain_name, None)

    def update_creds(self, chat_id: int, mode: int = CredMode.login):
        """
        User credentials update
        :param chat_id: chat id
        :param mode: CRED_MODE enum
        :return: writes to file and returns None
        """
        with open('creds.json') as json_file:
            data = json.load(json_file)

        if str(chat_id) not in data.keys():
            data[str(chat_id)] = {}
        if self.chain_name not in data[str(chat_id)].keys():
            data[str(chat_id)][self.chain_name] = {}

        if mode in (CredMode.login, CredMode.login_pwd):
            data[str(chat_id)][self.chain_name]['login'] = self.login
            data[str(chat_id)][self.chain_name]['password'] = self.password
        if mode in (CredMode.pwd, CredMode.login_pwd):
            data[str(chat_id)][self.chain_name]['cvv'] = self.cvv

        with open('creds.json', 'w') as outfile:
            json.dump(data, outfile)

    def change_state(self, display_name: str):
        if display_name in self.state_list:
            while self.state_list[-1] != display_name:
                self.state_list.pop()
        else:
            self.state_list.append(display_name)

        if len(self.state_list) == 1:
            self.login = None
            self.password = None
            self.cvv = None
        elif len(self.state_list) == 2:
            self.chain_name = self.state_list[1].lower()

        logging.info(self.state_list)


bot_state = defaultdict(BotState)


class Menu:
    def __init__(self, display_name: str, children: list):
        self.name = str(uuid.uuid4())
        self.display_name = display_name
        self.parent = None
        self.children = children

    def register(self, dispatcher):
        logging.debug( f'self.display_name {self.display_name}, {self.name}')
        dispatcher.add_handler(CallbackQueryHandler(self.display, pattern=self.name))
        for c in self.children:
            c.parent = self
            c.register(dispatcher)

    def display(self, update: Update, callback_context: CallbackContext):
        logging.debug(f'self.display_name {self.display_name}')
        logging.debug(f'self.keyboard() {self._keyboard()}')

        bs = bot_state[update.callback_query.message.chat.id]
        bs.change_state(self.display_name)
        update.callback_query.message.edit_text(self.display_name, reply_markup=self._keyboard())

    def create(self, update: Update, callback_context: CallbackContext, message = None):
        if not message:
            message = update.message
        bs = bot_state[message.chat.id]
        bs.change_state(self.display_name)
        message.reply_text(self.display_name, reply_markup=self._keyboard())

    def _keyboard(self):
        disp_len = 0
        res = []
        sub_res = []
        for c in self.children:
            disp_len += len(c.display_name)
            btn = InlineKeyboardButton(c.display_name, callback_data=c.name)
            if disp_len > 30:
                res.append(sub_res)
                disp_len = len(c.display_name)
                sub_res = [btn]
            else:
                sub_res.append(btn)

        res.append(sub_res)

        if self.parent:
            res.append([InlineKeyboardButton('Back to ' + self.parent.display_name, callback_data=self.parent.name)])

        return InlineKeyboardMarkup(res)


class ReplyMenu(Menu):
    def __init__(self, bot: Bot, display_name: str, children: list, next_menu: Menu=None):
        super().__init__(display_name, children)
        self.next_menu = next_menu
        self.bot = bot

    def display(self, update: Update, callback_context: CallbackContext):
        chat_id = update.callback_query.message.chat.id
        bs = bot_state[chat_id]
        creds = bs.get_creds(chat_id)
        bs.change_state(self.display_name)

        if not creds or self.display_name in ('Login', 'Payment'):
            if self.display_name == 'Login':
                msg = 'Please enter your login'
            elif self.display_name == 'Payment':
                msg = 'Please enter cvv for your card'
            else:
                raise ValueError('Unknown action!')
            #bs.last_message = update.callback_query.message.reply_text('Please enter your login')
            bs.last_message = self.bot.send_message(chat_id, msg, reply_markup=ForceReply())
            update.callback_query.message.delete()
        else:
            self.next_menu.display(update, callback_context)


class GroceriesBot:
    def __init__(self, token: str, chains: list):
        if not chains:
            ValueError('Empty chain list!')

        self.chains = chains
        self.bot = Bot(token)
        self.updater = Updater(bot=self.bot, use_context=True)

        self.m_root = None
        self.m_filter = {}
        self.m_settings = {}

        self.last_message = None

        self.create_menu()

    def create_menu(self):
        chain_menus = []
        for chain in self.chains:
            m_filtered_slots = Menu('Filtered slots', [])
            m_all_available_slots = Menu('All available slots', [])

            m_filter_slots = Menu('Filter slots', [m_filtered_slots])
            m_show_all_slots = Menu('Show all slots', [m_all_available_slots])

            self.m_filter[chain] = Menu('Filters', [m_filter_slots, m_show_all_slots])

            m_book_slot_and_checkout = ReplyMenu(self.bot, 'Book slot and checkout', [], self.m_filter[chain])
            m_book_slot = ReplyMenu(self.bot, 'Book slot', [], self.m_filter[chain])

            m_login = ReplyMenu(self.bot, 'Login', [])
            m_payment = ReplyMenu(self.bot, 'Payment', [])
            self.m_settings[chain] = Menu('Settings', [m_login, m_payment])

            m_chain = Menu(chain.capitalize(), [m_book_slot_and_checkout, m_book_slot, self.m_settings[chain]])
            self.m_filter[chain].parent = m_chain
            self.m_filter[chain].register(self.updater.dispatcher)

            chain_menus.append(m_chain)

        self.m_root = Menu('Main', chain_menus)
        self.updater.dispatcher.add_handler(CommandHandler('start', self.m_root.create))
        self.m_root.register(self.updater.dispatcher)
        self.updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, self.handle_text))

    def run(self):
        self.updater.start_polling()

    def handle_text(self, update: Update, context: CallbackContext):
        chat_id = update.message.chat.id
        bs = bot_state[chat_id]
        creds = bs.get_creds(chat_id)

        # the previous invitation
        if bs.last_message:
            bs.last_message.delete()

        if not creds or bs.state_list[-1] in ('Login', 'Payment'):
            cred_mode = CredMode.login
            if update.message.reply_to_message.text == 'Please enter your login': # bs.is_waiting_login:
                bs.login = update.message.text
                #bs.last_message = update.message.reply_text('Please enter your password')
                bs.last_message = self.bot.send_message(chat_id, 'Please enter your password', reply_markup=ForceReply())
            elif update.message.reply_to_message.text == 'Please enter your password':
                bs.password = update.message.text
                if bs.state_list[-1] in ('Book slot and checkout', 'Payment'):
                    if bs.state_list[-1] == 'Payment':
                        cred_mode = CredMode.pwd
                    else:
                        cred_mode = CredMode.login_pwd
                    #bs.last_message = update.message.reply_text('Please enter your cvv')
                    bs.last_message = self.bot.send_message(chat_id, 'Please enter cvv for your card',
                                                            reply_markup=ForceReply())
                else:
                    if bs.state_list[-1] == 'Login':
                        bs.change_state('Settings')
                        self.m_settings[bs.chain_name].create(None, None, update.message)
                    else:
                        bs.change_state('Filters')
                        self.m_filter[bs.chain_name].create(None, None, update.message)
            elif update.message.reply_to_message.text == 'Please enter cvv for your card':
                cred_mode = CredMode.pwd
                bs.cvv = update.message.text
                if bs.state_list[-1] == 'Payment':
                    bs.change_state('Settings')
                    self.m_settings[bs.chain_name].create(None, None, update.message)
                else:
                    bs.change_state('Filters')
                    self.m_filter[bs.chain_name].create(None, None, update.message)

            bs.update_creds(chat_id, cred_mode)
            # user's input
            update.message.delete()
        else:
            self.m_filter[bs.chain_name].create(None, None, update.message)
            bs.change_state('Filters')


if __name__ == '__main__':
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)
    b = GroceriesBot(BOT_TOKEN, CHAIN_LIST)
    b.run()
