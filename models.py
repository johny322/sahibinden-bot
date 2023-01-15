import json
from datetime import datetime

import pytz
from peewee import *
from peewee import Metadata
from playhouse.sqlite_ext import JSONField
from playhouse.sqliteq import SqliteQueueDatabase

db = SqliteQueueDatabase("base.db")


def get_datetime_now() -> datetime:
    return datetime.now(pytz.timezone("Europe/Moscow")).replace(tzinfo=None)


class BaseModel(Model):
    id = PrimaryKeyField(unique=True)
    created = DateTimeField(default=get_datetime_now)

    class Meta:
        database = db
        order_by = "id"


class User(BaseModel):
    user_id = IntegerField(unique=True)
    full_name = CharField()
    username = CharField(null=True)
    log_config = CharField(default="cfg_1_1_1_1_0_0_0_1_0_1_1_1_1")
    other_banned = BooleanField(default=False)
    black_words = BooleanField(default=False)

    class Meta:
        db_table = "users"


class BlackWord(BaseModel):
    owner = ForeignKeyField(User, backref="words")
    name = CharField()

    class Meta:
        db_table = "black_words"


class SahibindenBanned(BaseModel):
    owner = ForeignKeyField(User)
    seller = CharField()  # seller id

    class Meta:
        db_table = "sahibinden_bans"


# class DehandsPreset(BaseModel):
#     owner = ForeignKeyField(User)
#     name = CharField()
#     query = CharField()
#     reg_date = DateTimeField(null=True)
#     post_date = DateTimeField(null=True)
#     max_rating = IntegerField(null=True)
#     price_s = IntegerField()
#     price_e = IntegerField()
#     max_views = IntegerField(null=True)
#     max_posts = IntegerField(null=True)
#
#     class Meta:
#         db_table = "dehands_presets"


class ParserBanned(BaseModel):
    owner = ForeignKeyField(User)
    # parser_name = CharField()
    seller = CharField()

    class Meta:
        db_table = "parsers_banned"


class ParserFirstBanned(BaseModel):
    # owner = ForeignKeyField(User)
    # parser_name = CharField()
    search_url = CharField()
    post = CharField()

    class Meta:
        db_table = "parsers_last_banned"


class Parser(BaseModel):
    owner = ForeignKeyField(User)
    # parser_name = CharField()
    pars_filter = JSONField()
    url = CharField()
    start_page_number = IntegerField(default=1)
    first_pars = BooleanField(default=True)

    class Meta:
        db_table = "parsers"


class Post(BaseModel):
    owner = ForeignKeyField(User)
    # parser_name = CharField()
    post_json = JSONField()

    class Meta:
        db_table = "posts"


class Alert(BaseModel):
    message = CharField()

    class Meta:
        db_table = "alerts"


db.create_tables([
    User, BlackWord,
    Parser,
    ParserFirstBanned,
    ParserBanned,
    Post,
    Alert,
])

ALL_BANNED = [
    ParserBanned
]

ALL_PRESETS = [
    # DehandsPreset
]

ALL_PRESETS_DICT = {preset._meta.table_name: preset for preset in ALL_PRESETS}

# from playhouse.migrate import *
# migrator = SqliteMigrator(db)
# try:
#     with db.atomic():
#         try:
#             migrate(
#                 migrator.add_column('parsers', 'start_page_number', IntegerField(default=1)),
#             )
#         except Exception as e:
#             print(e)
#             pass
#
# except:
#     pass

if __name__ == '__main__':
    # parsers = Parser.select().group_by(Parser.url)
    # uniq_urls = [parser.url for parser in parsers]
    # print(uniq_urls)
    # for uniq_url in uniq_urls:
    #     parsers = Parser.select().where(Parser.url == uniq_url)
    #     for parser in parsers:
    #         print(parser.owner.user_id)
    # pars_filter = dict(
    #     name='name',
    #     title='tile'
    # )
    # Parser.create(
    #     owner=1,
    #     pars_filter=pars_filter,
    #     url='12312321'
    # )
    # pars_filter = Parser.get(id=1).pars_filter
    # print(type(pars_filter))
    parsers = User.select().first()
    print(parsers)
    # i = 0
    # while i < 3:
    #     parsers = Parser.select()
    #     if parsers:
    #         print('parsers')
    #     else:
    #         print('no parsers')
    #     for parser in parsers:
    #         print(parser.first_pars)
    #         if parser.first_pars:
    #             parser.first_pars = False
    #         parser.save()
    #         # parser.delete().execute()
    #     i += 1
