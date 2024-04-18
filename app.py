import os
from flask import Flask, render_template, request, redirect, url_for
import xml.etree.ElementTree as ET
from werkzeug.utils import secure_filename
import sqlite3
import time

db_name = 'my_data_base.db'
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def parse_xml(file_contents):
    root = ET.fromstring(file_contents)
    objects = []
    for obj in root.findall('.//mxCell'):
        obj_data = {}
        obj_data['id'] = obj.get('id')
        obj_data['value'] = obj.get('value')
        obj_data['source'] = obj.get('source')
        obj_data['target'] = obj.get('target')
        objects.append(obj_data)

    return objects


def create_table(objects, filename):
    count = 0
    tables = get_existing_tables()
    for table in tables:
        if table == filename:
            count += 1
    if count == 0:
        connect = sqlite3.connect(db_name)
        cursor = connect.cursor()
        cursor.execute(f'''CREATE TABLE IF NOT EXISTS {filename}(
                          id TEXT PRIMARY KEY,
                          value TEXT,
                          source TEXT,
                          target TEXT,
                          description TEXT, 
                          type TEXT)''')

        connect.commit()

        for obj in objects:
            if obj['source'] is not None and obj['target'] is not None and len(obj['id']) > 2:
                cursor.execute(
                    f"INSERT INTO {filename} (id, value, source, target, description, type) VALUES (?, ?, ?, ?, ?, ?)",
                    (obj['id'], obj['value'], obj['source'], obj['target'], '', 'relationship'))
            elif obj['source'] is None and obj['target'] is None and len(obj['id']) > 2:
                cursor.execute(
                    f"INSERT INTO {filename} (id, value, source, target, description, type) VALUES (?, ?, ?, ?, ?, ?)",
                    (obj['id'], obj['value'], obj['source'], obj['target'], '', 'object'))
        connect.commit()
    else:
        print('')

def get_table_data(table_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    data = cursor.fetchall()
    conn.close()
    return data


def get_existing_tables():
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    conn.close()
    return [table[0] for table in tables]


@app.route('/', methods=['GET', 'POST'])
def home_page():
    if request.method == 'POST':
        uploaded_file = request.files['file']
        if uploaded_file:
            filename = secure_filename(uploaded_file.filename)
            file_contents = uploaded_file.read().decode('utf-8')
            objects = parse_xml(file_contents)
            full_filename = str(time.time_ns()) + filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            uploaded_file.save(file_path)
            str_filename = filename.split('.')[0]
            create_table(objects, filename=str_filename)

            return redirect(url_for('home_page'))
    return render_template('index.html')


@app.route('/data_base')
def data_base_view():
    data = get_existing_tables()
    return render_template('database_export.html', data=data)

@app.route('/table_view/<table_name>')
def table_view(table_name):
    diagramm = []
    data = get_table_data(table_name)
    for i in range(0, len(data)):
        rel = []
        start_point = ''
        end_point = ''
        val = ''
        if data[i][-1] == 'relationship':
            start_point = data[i][2]
            end_point = data[i][3]
            val = data[i][1]

            for j in range(0, len(data)):
                if data[j][0] == start_point:
                    rel.append(data[j][1])
            rel.append(val)
            for j in range(0, len(data)):
                if data[j][0] == end_point:
                    rel.append(data[j][1])

            diagramm.append(rel)
    return render_template('table_view.html', data=data, table_name=table_name, diagramm=diagramm)

@app.route('/termins/<table_name>')
def termins_view(table_name):

    data = get_table_data(table_name)

    return render_template('termins.html', data=data, table_name=table_name)

@app.route('/edit_values/<table_name>', methods=['GET'])
def edit_values(table_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    table_data = cursor.fetchall()
    conn.close()
    return render_template('edit_values.html', table_data=table_data, table_name=table_name)


@app.route('/update_values/<table_name>', methods=['POST'])
def update_values(table_name):
    for key, value in request.form.items():
        if key.startswith('value_'):
            row_id = key.split('_')[1]
            conn = sqlite3.connect(db_name)
            cursor = conn.cursor()
            cursor.execute(f"UPDATE {table_name} SET value=? WHERE id=?", (value, row_id))
            conn.commit()
            conn.close()
    return redirect(url_for('table_view', table_name=table_name))


@app.route('/edit_desc/<table_name>', methods=['GET'])
def edit_desc(table_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    table_data = cursor.fetchall()
    conn.close()
    return render_template('edit_desc.html', table_data=table_data, table_name=table_name)


@app.route('/update_description/<table_name>', methods=['POST'])
def update_description(table_name):
    for key, value in request.form.items():
        if key.startswith('value_'):
            row_id = key.split('_')[1]
            conn = sqlite3.connect(db_name)
            cursor = conn.cursor()
            cursor.execute(f"UPDATE {table_name} SET description=? WHERE id=?", (value, row_id))
            conn.commit()
            conn.close()
    return redirect(url_for('table_view', table_name=table_name))

@app.route('/description/<table_name>')
def description(table_name):
    terms = []
    table_data = get_table_data(table_name)
    for i in range(0, len(table_data)):
        term = []
        if table_data[i][1] is not None:
            term.append(table_data[i][1])
            term.append(table_data[i][4])
        if term != []:
            terms.append(term)

    return render_template('description.html', table_name=table_name, table_data=table_data, terms=terms)

if __name__ == '__main__':
    app.run(debug=True, port=9000)
