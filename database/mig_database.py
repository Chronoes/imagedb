"""
"""
import sys
import os.path

from peewee import *

import database as new_db

__author__ = 'Chronoes'


db_path = os.path.join(os.path.dirname(__file__), 'imageDB.sqlite.old')
db = SqliteDatabase(db_path)

class BaseModel(Model):
    class Meta:
        database = db

class Image(BaseModel):
    filename = CharField(unique=True)
    path = CharField()
    original_link = CharField()


class Tag(BaseModel):
    tag = CharField(unique=True)

class ImageTag(BaseModel):
    image = ForeignKeyField(Image)
    tag = ForeignKeyField(Tag)

    class Meta:
        primary_key = False

db.connect()

if __name__ == '__main__':
    tags = [{'tag': tag.tag} for tag in Tag.select()]
    with new_db.db.atomic():
        for chunk in range(0, len(tags), 200):
            new_db.Tag.insert_many(tags[chunk:chunk + 200]).execute()

    image_groups = [{'name': 'lewd', 'path': 'E:\\Hentai\\images'}, {'name': 'wallpaper', 'path': 'E:\\Wallpaper'}, {'name': 'regular', 'path': 'E:\\images'}]
    db_image_groups = {}

    with new_db.db.atomic():
        for group in image_groups:
            db_group = new_db.ImageGroup.create(**group)
            db_image_groups[db_group.path] = db_group

    with new_db.db.atomic():
        for image in Image.select():
            new_img = new_db.Image.create(
                filename=image.filename,
                original_link=image.original_link,
                group=db_image_groups[image.path]
            )

            image_tags = [tag.tag for tag in Tag.select().where(ImageTag.image == image).join(ImageTag)]
            if len(image_tags) > 0:
                tags = new_db.Tag.select().where(new_db.Tag.tag << image_tags)
                new_db.ImageTag.insert_many({'image': new_img, 'tag': tag} for tag in tags).execute()
            else:
                print(image.filename)
                # select * from image left join imagetag on (image.id = imagetag.image_id) group by image.id having count(imagetag.image_id) = 0;
