from .database import ImageTag, Image, ImageGroup, Tag

def imagetag_subquery(tag):
    return ImageTag.select(ImageTag.image).where(Tag.tag.startswith(tag)).join(Tag)

def query_results(split_line: list, groups=None, query_type='keyword'):
    query = Image.select() \
        .order_by(Image.id.desc()) \
        .join(ImageGroup)

    if groups is not None and len(groups) > 0:
        query = query.where(ImageGroup.id << groups)

    if query_type == 'filename':
        ilike_qry = '{}%'
        query = query.where(Image.filename ** ilike_qry.format(split_line[0]))
        for filename in split_line[1:]:
            query |= Image.filename ** ilike_qry.format(filename)
        return query
    else:
        imagetags = imagetag_subquery(split_line[0])
        for tag in split_line[1:]:
            imagetags &= imagetag_subquery(tag)
        return query.where(Image.id << imagetags).group_by(Image.id)


def query_by_id(ids: list):
    query = Image.select().where(Image.id << ids).join(ImageGroup)
    return list(query)

def find_group(group: str):
    return ImageGroup.get(ImageGroup.name == group)

def get_groups():
    return ImageGroup.select()

def get_image_tags(img):
    return (tag.tag for tag in Tag.select(Tag.tag).where(ImageTag.image == img).join(ImageTag))
