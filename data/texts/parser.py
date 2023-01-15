import datetime

from data import texts

parser_get_posts = "Получил <b>{count_posts} обьявлений</b>, ищу подходящие"
parser_many_get_posts = """\
По ссылке {url}
Получил <b>{count_posts} обьявлений</b>, ищу подходящие
"""

parse_count = "Сколько нужно спарсить обьявлений?"
parse_count_invalid = "Введите число а не текст"
parse_count_too_much = "Число слишком большое, укажите меньше <b>{max_count}</b>"

all_urls_text = """
Список ссылок:
{urls}

Для удаления ссылки отправьте команду /del с ссылкой
Пример: <b>/del {url}</b>
"""

invalid_pars_url_del = """
Кажется вы не отправили ссылку

Для удаления ссылки отправьте команду /del с ссылкой
Пример: <b>/del https://mobil.bazos.cz/</b>
"""

parse_post_date = """\
Укажите дату создания объявления

Отправьте 'no' чтобы пропустить фильтр
"""

parse_creator_date = """\
Укажите дату регистрации продавца

Отправьте 'no' чтобы пропустить фильтр
"""

parse_business_account = """\
Собирать объявления бизнес аккаунтов? 
"""

parse_date_invalid = "Неверный формат даты, повторите ввод или отправьте 'no' чтобы пропустить фильтр"

parse_price = """
Введите диапазон цены (в {coin}) товара:

<b>Пример: 100-800</b>
"""

parse_currency = """
Выберите валюту: {currencies}
"""

bad_parse_currency = """
Неверная валюта
Выберите из значений: {currencies}
"""

parse_price_invalid = "Вы указали диапазон неправильно! Введите еще раз."

parse_seller_posts = """
Введите число кол-во обьявлений продавца

Пример: 10 (парсер будет искать продавцов у которых кол-во обьявлений не будет превышать 10)

Если вы хотите отключать этот фильтр нажмите 'no'
"""

parse_seller_rating = """
Введите число рейтинга продавца

Пример: 3 (парсер будет искать продавцов, у которых рейтинг меньше, либо равен 3)

Если вы хотите отключать этот фильтр нажмите 'no'
"""

parse_seller_reviews = """
Введите число отзывов продавца

Пример: 3 (парсер будет искать продавцов, у которых отзывов меньше, либо равно 3)

Если вы хотите отключать этот фильтр нажмите 'no'
"""

parse_post_views = """
Введите число кол-во просмотров объявления

Пример: 10 (парсер будет искать объявления у которых кол-во просмотров не будет превышать 10)

Если вы хотите отключать этот фильтр нажмите 'no'
"""

parse_taken_item_count = """
Введите число кол-во купленных товаров продавцом

Пример: 10 (парсер будет искать объявления у которых кол-во купленных товаров продавцом не будет превышать 10)

Если вы хотите отключать этот фильтр нажмите 'no'
"""

parse_given_item_count = """
Введите число кол-во проданных товаров продавцом

Пример: 10 (парсер будет искать объявления у которых кол-во проданных товаров продавцом не будет превышать 10)

Если вы хотите отключать этот фильтр нажмите 'no'
"""

parse_reports_received_count = """
Введите число кол-во успешных доставок продавцом

Пример: 10 (парсер будет искать объявления у которых кол-во успешных доставок продавцом не будет превышать 10)

Если вы хотите отключать этот фильтр нажмите 'no'
"""

parse_seller_posts_invalid = """
Введите <b>правильное число</b> кол-во обьявлений продавца

Если вы хотите отключать этот фильтр нажмите 'no'
"""

parse_seller_rating_invalid = """
Введите <b>правильное число</b> минимального рейтинга продавца

Если вы хотите отключать этот фильтр нажмите 'no'
"""

parse_seller_reviews_invalid = """
Введите <b>правильное число</b> минимального числа отзывов продавца

Если вы хотите отключать этот фильтр нажмите 'no'
"""

parse_post_views_invalid = """
Введите <b>правильное число</b> кол-во просмотров объявления

Если вы хотите отключать этот фильтр нажмите 'no'
"""

parse_taken_item_count_invalid = """
Введите <b>правильное число</b> кол-во купленных товаров

Если вы хотите отключать этот фильтр нажмите 'no'
"""

parse_given_item_count_invalid = """
Введите <b>правильное число</b> кол-во проданных товаров

Если вы хотите отключать этот фильтр нажмите 'no'
"""

parse_reports_received_count_invalid = """
Введите <b>правильное число</b> кол-во успешных доставок

Если вы хотите отключать этот фильтр нажмите 'no'
"""

presets = "Выберите нужный пресет"

parse_save_preset = """
💾 Вы хотите сохранить настройки парсера?

<b>'yes' - сохранить</b> (если вы сохранить настройки то вы сможете найти их в пресетах)

<b>'no' - не сохранять</b>
"""


def get_preset_settings_text(data):
    text = []
    if data.get('name') is not None:
        text.append(f"Имя: <b>{data.get('name')}</b>")
    if data.get('price') is not None:
        text.append(f"Рамки цены: <b>{data.get('price')} {data.get('currency')}</b>")
    if data.get('max_posts') is not None:
        text.append(f"Кол-во обьявлений у продавца: <b>{data.get('max_posts')}</b>")
    if data.get('max_rating') is not None:
        text.append(f"Максимальный рейтинг продавца: <b>{data.get('max_rating')}</b>")
    if data.get('max_views') is not None:
        text.append(f"Кол-во просмотров: <b>{data.get('max_views')}</b>")
    if data.get('reg_date') is not None:
        text.append(f"Дата регистрации продавца: <b>{data.get('reg_date')}</b>")
    if data.get('post_date') is not None:
        text.append(f"Дата выпуска объявления: <b>{data.get('post_date')}</b>")

    return '\n'.join(text)


preset_settings = """
Настройки вашего пресета:
{settings}
Введите кол-во товара:

<b>Пример: 100</b>
"""

preset_save_name = "Введите название пресета"

preset_saved = "Пресет успешно сохранен"
preset_alredy_exists = "Пресет с таким названием уже есть, пресет не создан!"
parse_url = """\
Введите вашу ссылку с фильтрами
(необходимо использовать ссылку на английский перевод сайта - /en/ в ссылке):

<b>Пример ссылки: {parser_link}</b>
"""
parse_many_urls = """\
Введите вашу ссылки с фильтрами или слова
(каждая ссылка или слово на новой строке):

<b>Пример ссылки: {parser_link}</b>
<b>Пример слова: Apple</b>
"""

# parse_start_sub = "🟢 Подписка закончится <b>{date}</b>"
parse_start_sub = 'Выберите нужный пункт'
parse_starts = "<b>Парсинг начинается</b> 🤖"
parse_ends = "<b>Парсинг закончился</b> 💋\n"


def parser_text_end(skip_data):
    text = ['Объявления не подошедшие']
    if skip_data.get('skip_post_price') is not None:
        text.append(f"По цене объявления: {skip_data.get('skip_post_price')}")
    if skip_data.get('skip_post_date') is not None:
        text.append(f"По дате объявления: {skip_data.get('skip_post_date')}")
    if skip_data.get('skip_reg_date') is not None:
        text.append(f"По дате регистрации: {skip_data.get('skip_reg_date')}")
    if skip_data.get('skip_max_posts') is not None:
        text.append(f"По кол-ву постов: {skip_data.get('skip_max_posts')}")
    if skip_data.get('skip_max_views') is not None:
        text.append(f"По кол-ву просмотров: {skip_data.get('skip_max_views')}")
    if skip_data.get('skip_max_rating') is not None:
        text.append(f"По рейтингу продавца: {skip_data.get('skip_max_rating')}")

    if skip_data.get('skip_only_phone') is not None:
        text.append(f"Без номера: {skip_data.get('skip_only_phone')}")
    if skip_data.get('skip_ban_word') is not None:
        text.append(f"Слово в чс: {skip_data.get('skip_ban_word')}")
    if skip_data.get('skip_ban_post') is not None:
        text.append(f"Обьявление в чс: {skip_data.get('skip_ban_post')}")
    if skip_data.get('anythink_skip') is not None:
        text.append(f"Другая причина: {skip_data.get('anythink_skip')}")
    if skip_data.get('all_count') is not None:
        text.append(f"Всего пропущено: {skip_data.get('all_count')}")

    return '\n'.join(text)


parse_interrupted = "Парсинг завершён досрочно!"

parser_texts = "Выберите нужный текст"

parser_text_info = """
<b>{name}</b>

<i>{text}</i>
"""

new_text_without_seller = """
<b>Введите ваш текст старта для WhatsApp</b>

Доступные слова вставки:
<code>@link</code> - Подставит текущую ссылку
<code>@price</code> - Подставит цену товара
<code>@itemname</code> - Подставит название товара

🟦 Вы можете указать слово вставку и вместо него подставится нужная информация
"""

new_text = """
<b>Введите ваш текст старта для WhatsApp</b>

Доступные слова вставки:
<code>@link</code> - Подставит текущую ссылку
<code>@seller</code> - Подставит имя продавца
<code>@price</code> - Подставит цену товара
<code>@itemname</code> - Подставит название товара

🟦 Вы можете указать слово вставку и вместо него подставится нужная информация
"""
new_text_name = "Придумайте название своему тексту старта WhatsApp"
new_text_name_exists = "Текст с таким названием уже есть у вас"

choice_parser_country = "<b>Выберите площадку, где вы хотите найти объявления</b>"


class PostFromDict:
    def __init__(self, data: dict):
        for key, val in data.items():
            setattr(self, key, val)


def create_result_text(post, log, extra: dict):
    text = "📦 Товар"
    if log.title and hasattr(post, 'title'):
        text += f": <code>{post.title}</code>\n"
    if log.description and hasattr(post, 'description'):
        text += f"😇 Описание: <i>{post.description}</i>\n"
    if log.price:
        currency = extra.get('currency', '')
        text += f"💰 Цена: <b>{post.price} {currency}</b>\n\n"
    if log.location and hasattr(post, 'town'):
        text += f"📍 Местоположение товара: {post.town}\n\n"
    # if post.phone and hasattr(post, 'phone'):
    #     text += f"📞 Контакт(-ы): <code>{post.phone}</code>\n"
    #     text += f"WhatsApp: <a href='https://api.whatsapp.com/send?phone={post.phone}'>Клик</a>\n"
    #     text += f"🖥 WEB WhatsApp: <a href='https://web.whatsapp.com/send?phone={post.phone}'>Клик</a>\n\n"
    #     text += texts.goviber.format(phone=post.phone)
    #     text += texts.gotelegram.format(phone=post.phone) + "\n"
    #     wa_texts = extra.get('wa_texts')
    #     if wa_texts:
    #         wa_web_text = " ".join(list(map(lambda t: t[0], wa_texts)))
    #         wa_mob_text = " ".join(list(map(lambda t: t[1], wa_texts)))
    #         text += f"📱 WhatsApp (Ваш текст): {wa_mob_text}\n" + \
    #                 f"🖥 WEB WhatsApp (Ваш текст): {wa_web_text}\n\n"
    # if log.views and hasattr(post, 'views'):
    #     text += f"👁 Просмотров: {post.views}\n"
    if log.created and hasattr(post, 'created'):
        created = post.created.strftime('%Y-%m-%d') if isinstance(post.created, datetime.datetime) else post.created
        text += f"🗓 Дата создания объявления: <b>{created}</b>\n"
    if log.seller_reg and hasattr(post, 'seller_reg'):
        seller_reg = post.seller_reg.strftime('%Y-%m-%d') if isinstance(post.seller_reg, datetime.datetime) \
            else post.seller_reg
        text += f"🗓 Дата регистрации продавца: <b>{seller_reg}</b>\n"
    if log.posts_count and hasattr(post, 'seller_posts'):
        text += f"🔢 Обьявлений продавца: {post.seller_posts}\n"
    text += f"🔗 Ссылка на товар: <a href='{post.link}'>Нажми</a>\n"

    if hasattr(post, 'photo_url'):
        if post.photo_url:
            text += f"🔗 Ссылка на фото: <a href='{post.photo_url}'>Нажми</a>\n"

    if log.seller_name and hasattr(post, 'seller_name'):
        text += f"👨 Имя продавца: <b>{post.seller_name}</b>\n"

    if hasattr(post, 'seller_rating'):
        text += f'⭐ Рейтинг продавца <b>{post.seller_rating}</b>\n'

    if hasattr(post, 'seller_reviews'):
        text += f'⭐ Число отзывов продавца <b>{post.seller_reviews}</b>\n'

    return text


start_parsing_text = 'Ссылка успешно добавлена. Парсинг начнется автоматически'
