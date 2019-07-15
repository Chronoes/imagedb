import os
import os.path
import shutil
import json

import imagedb.database as db

from imagedb.database.db_queries import query_results, find_group, get_groups, get_image_tags, query_by_id
from flask import Flask, render_template, request, send_from_directory, url_for
from imagedb.config import load_config

app = Flask(__name__)
config = load_config()

@app.context_processor
def override_url_for():
    return dict(url_for=dated_url_for)

def dated_url_for(endpoint, **values):
    if endpoint == 'static':
        filename = values.get('filename', None)
        if filename:
            file_path = os.path.join(app.root_path,
                                     endpoint, filename)
            values['q'] = int(os.stat(file_path).st_mtime)
    return url_for(endpoint, **values)


@app.route('/')
def index():
    defaults = {
        'groups': list(get_groups()),
        'qt': 'keyword'
    }
    keywords = request.args.get('keywords')
    if keywords:
        defaults['qt'] = request.args.get('qt', defaults['qt'])
        results = []
        query = query_results(keywords.split(), groups=request.args.getlist('ig[]'), query_type=defaults['qt'])
        for image in query:
            results.append((image, ' '.join(get_image_tags(image))))

        return render_template('index.html', keywords=keywords, results=results, **defaults)

    return render_template('index.html', **defaults)

@app.route('/image/<int:image_id>', methods=['PUT', 'DELETE'])
def image(image_id):
    if request.method == 'PUT':
        image = query_by_id([image_id]).pop()

        if request.form.get('ig'):
            new_group = db.ImageGroup.get(db.ImageGroup.id == request.form.get('ig'))
            if new_group:
                old_directory = config['groups'][image.group.name]
                new_directory = config['groups'][new_group.name]

                image_path = os.path.join(old_directory, image.filename)
                if os.path.exists(os.path.join(new_directory, image.filename)):
                    if os.path.exists(image_path):
                        os.remove(image_path)
                else:
                    shutil.move(image_path, new_directory)
                image.group = new_group

        image.save()
    if request.method == 'DELETE':
        image = query_by_id([image_id]).pop()

        image.delete_instance()

        directory = config['groups'][image.group.name]
        try:
            os.remove(os.path.join(directory, image.filename))
        except FileNotFoundError:
            pass

    return 'success'

@app.route('/<group>/<path:filename>')
def image_file(group, filename):
    db_group = find_group(group)
    if db_group:
        directory = config['groups'][db_group.name]
        return send_from_directory(directory, filename)
    return None
