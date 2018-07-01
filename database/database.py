"""
"""
import os.path
import peewee as pw

__author__ = 'Chronoes'

db_path = os.path.join(os.path.dirname(__file__), 'imageDB.sqlite')
db = pw.SqliteDatabase(db_path)

class BaseModel(pw.Model):
    class Meta:
        database = db

class ImageGroup(BaseModel):
    name = pw.CharField(unique=True)
    path = pw.CharField()

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

db.connect()
models = [ImageGroup, Image, Tag, ImageTag]
db.create_tables(models, safe=True)
