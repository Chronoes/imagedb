"""
"""
import os.path
import peewee as pw

from imagedb.config import load_config

__author__ = 'Chronoes'
config = load_config()

db = pw.SqliteDatabase(config['database']['path'])

class BaseModel(pw.Model):
    class Meta:
        database = db

class ImageGroup(BaseModel):
    name = pw.CharField(unique=True)

class Image(BaseModel):
    group = pw.ForeignKeyField(ImageGroup)
    filename = pw.CharField(unique=True)
    original_link = pw.CharField()

class Tag(BaseModel):
    tag = pw.CharField(unique=True)

class ImageTag(BaseModel):
    image = pw.ForeignKeyField(Image)
    tag = pw.ForeignKeyField(Tag)

    class Meta:
        primary_key = pw.CompositeKey('image', 'tag')

connected = False

def connect_db():
    global connected
    if connected:
        return db

    db.connect()
    models = [ImageGroup, Image, Tag, ImageTag]
    db.create_tables(models, safe=True)
    connected = True
    return db
