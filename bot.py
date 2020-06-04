import os
import re
import cv2
import shutil
import telebot
import numpy as np
import urllib.request
from PIL import Image, ImageFilter

TOKEN = '1220648131:AAEsQlHIPFrqzxdMqOgh36NDwTQ2KwfZT_g'
bot = telebot.TeleBot(TOKEN)

RESULT_STORAGE_DIR = 'temp'
PARAMS = dict()
BLUR_RADIUS = 3

keyboard1 = telebot.types.ReplyKeyboardMarkup(True, True)
keyboard1.row('RGB', 'RG')

help1 = 'http://i.piccy.info/i9/00c30f3d5f6fdccfc7062799858b258d/1591025120/463501/1374772/BOTFON.jpg'


def get_image_id_from_message(message):
    return message.photo[len(message.photo) - 1].file_id


def save_image_from_message(message):
    image_id = get_image_id_from_message(message)
    # подготовка к загрузке
    file_path = bot.get_file(image_id).file_path

    # создание ссылки загрузки
    image_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"

    image_name = f"{image_id}.png"
    urllib.request.urlretrieve(image_url, f"{RESULT_STORAGE_DIR}/{image_name}")
    return image_name


def is_correct_mode(sentence):
    is_correct = re.match(r'^[rgb]+$', sentence)
    return bool(is_correct)


def preprocess_sentence(sentence):
    sentence = re.sub(r'\W+', '', sentence.lower().strip())  # Delete special symbols
    sentence = re.sub(r'([a-z])\1+', r'\1', sentence)  # Remove duplicates
    return sentence


def get_image_capture_params(message):
    caption = message.caption

    if caption is not None:
        prs_params = [param.strip() for param in re.split(r'\W+', caption.strip())]

        if len(prs_params) == 2:
            params = dict()
            mode = preprocess_sentence(prs_params[0])
            params['mode'] = mode if is_correct_mode(mode) else None
            params['percent'] = float(prs_params[-1]) if prs_params[-1].lstrip('-').isdigit() and  -10 <= float(prs_params[-1]) <= 10 else None
            if not None in [params['mode'], params['percent']]:
                return params

        bot.send_message(chat_id=message.chat.id, text=f'Bad caption (use \help command for help): {caption}')
    return None


def sharp(image, radius, percent):
    # Median filtering
    blur = cv2.medianBlur(image, radius)

    # Calculate the Laplacian
    lap = cv2.Laplacian(blur, cv2.CV_64F)

    # Calculate the sharpened image
    sharp = image - lap * percent

    # Saturate the pixels in either direction
    sharp[sharp > 255] = 255
    sharp[sharp < 0] = 0
    return sharp


def filter_image(image_name, params):
    content_image = cv2.imread(f"{RESULT_STORAGE_DIR}/{image_name}")

    mode = list(params['mode'])
    percent = params['percent'] * 2 / 10

    RGB = {'r': 2,
           'g': 1,
           'b': 0}

    for chanel in mode:
        content_image[:, :, RGB[chanel]] = sharp(content_image[:, :, RGB[chanel]], BLUR_RADIUS, percent)

    sharp_image_filename = f'sharp_{image_name}'
    cv2.imwrite(f"{RESULT_STORAGE_DIR}/{sharp_image_filename}", content_image)
    return sharp_image_filename


def process_image(message, image_name, params):
    sharp_image_filename = filter_image(image_name, params=params)

    bot.send_message(chat_id=message.chat.id, text='Не, ну нормас вышло!')
    bot.send_photo(message.chat.id, open(f'{RESULT_STORAGE_DIR}/{sharp_image_filename}', 'rb'),
                   caption=f'Я вот шо использовал:\nТип: {params["mode"].upper()}\nПроцент: {params["percent"]}')
    bot.send_message(chat_id=message.chat.id,
                     text='''Не, ну ты нормас, кстати.Если хочешь, давай еще раз обработаем.
                     \nИ да, раз уж ты такой опытный теперь, следующий раз можешь отправить мне картинку и сразу же к ней прикрепить значения.
                     \nЭто будет шото вроде RGB -3 или же RG 5''')

    # Clear
    cleanup_remove_images(image_name, sharp_image_filename)
    PARAMS[message.chat.id] = None


def cleanup_remove_images(image_name, image_name_new):
    os.remove(f'{RESULT_STORAGE_DIR}/{image_name}')
    os.remove(f'{RESULT_STORAGE_DIR}/{image_name_new}')


def clear_chat_info(chat_id):
    PARAMS[chat_id] = None


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, 'Салют! Я чёткий бот, давай быро обработаю твою фотку! Придам ей чёткости.'
                                      'Если чё, смотри как я работаю в /help', parse_mode='html')


@bot.message_handler(commands=['help'])
def help_handler(message):
    bot.send_message(message.chat.id, '''Так от, как я работаю?
    \nНадо, шоб ты загрузил фотку в меня и я ее обработаю! Только надо, шоб ты выбрал модификацию.
    \nЧё такое модификация спрашиваешь? Короче, я могу придать чёткости либо на всю фотографию, либо только на красные и
    на зелёные участки твоей фотки. Выбирать тебе. Если хочешь на всю - нажми на RGB, а если на отдельные каналы - RG.
    \nА потом введи значение от - 10 до 10. Я тебе еще подскажу как выглядит картинка при - 10, а как при 10. 
    \nКороче, если нет вопросов - давай, загружай фотку и всё сделаем чётко!''', parse_mode='html')


@bot.message_handler(content_types=['text'])
def handle_text(message):
    cid = message.chat.id

    if PARAMS.get(cid) is not None:
        if PARAMS[cid].get('mode') is None:
            if is_correct_mode(preprocess_sentence(message.text)):
                PARAMS[cid]['mode'] = preprocess_sentence(message.text)
                bot.send_message(chat_id=cid, text='Нормас, а теперь выбери от -10 до 10. И да, как обещал, ниже пример')
                bot.send_photo(message.chat.id, help1)
            else:
                bot.send_message(chat_id=cid, text='Ненене, совсем не то. У тебя только 2 варика - или RGB, или RG.')
        else:
            if message.text.lstrip('-').isdigit():
                if -10 <= float(message.text) <= 10:
                    PARAMS[cid]['percent'] = float(message.text)
                    process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                    clear_chat_info(cid)
                else:
                    bot.send_message(chat_id=cid, text='Совсем не то, ты чё. Нужно число от -10 до 10, не путай.')
            else:
                bot.send_message(chat_id=cid, text='Та цифры нужны, не буквы. ')
    else:
        bot.send_message(chat_id=cid, text='Я шото не вижу картинки, загрузи - потом поговорим.')


@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    cid = message.chat.id

    # Get the image
    image_name = save_image_from_message(message)
    bot.send_message(chat_id=cid, text='Окей, я сохранил, щас всё сделаем.')

    # get params from image capture if exist
    params = get_image_capture_params(message)

    if params is not None:  # If params were sent with Image capture
        bot.send_message(chat_id=message.chat.id, text='Окей, как скажешь.\nЩа сделаем...')
        params['image'] = image_name

        process_image(message, image_name, params)

    else:
        PARAMS[cid] = {
            'image': image_name
        }
        bot.send_message(chat_id=message.chat.id, text='Лады, а теперь выбери что именно изменять:', reply_markup=keyboard1)


if __name__ == '__main__':
    try:
        if not os.path.exists(RESULT_STORAGE_DIR):
            os.makedirs(RESULT_STORAGE_DIR)
        bot.polling()
    except Exception as e:
        print(e)
    finally:
        if os.path.exists(RESULT_STORAGE_DIR):
            shutil.rmtree(RESULT_STORAGE_DIR)
