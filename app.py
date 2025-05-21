from flask import Flask, render_template, request, send_file, jsonify
import os
import pandas as pd
import requests
from flask_cors import CORS
import matching_walid  # ton module de matching

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_FOLDER = os.path.join(BASE_DIR, 'static')
PROCESSED_FOLDER = os.path.join(BASE_DIR, 'processed')
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/student-choices')
def student_choices():
    SHEET_URL = 'https://script.google.com/macros/s/AKfycbx_bnOaWmgWdbK3wBcloxWxo4QxJYA7o69LQoEj2WYWKjPJ9CD3vu0O1Y6wZChrkcy3PQ/exec'
    try:
        response = requests.get(SHEET_URL)
        response.raise_for_status()
        data = response.json()
        return jsonify(data)
    except Exception as e:
        print("Erreur :", e)
        return jsonify([]), 500


@app.route('/run-matching', methods=['GET', 'POST'])
def run_matching():
    project_path = os.path.join(STATIC_FOLDER, 'projects.csv')

    # IMPORTANT : lien vers Google Sheet publié en CSV (doit être un lien direct CSV)
    SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1y8dabxt5kMxbFPePS288vZHwW5jQlPfB67TOODqZdbI/export?format=csv&gid=0"
    
    try:
        response = requests.get(SHEET_CSV_URL)
        response.raise_for_status()
    except Exception as e:
        return f"Erreur lors du téléchargement du fichier CSV: {e}", 500

    student_path = os.path.join(PROCESSED_FOLDER, 'students.csv')
    with open(student_path, 'wb') as f:
        f.write(response.content)

    output_path = os.path.join(PROCESSED_FOLDER, 'assignments.xlsx')
    df_result = matching_walid.run_matching(project_path, student_path, output_path)

    table_html = df_result.to_html(classes='csv-preview', index=False)
    return render_template('preview.html', table=table_html, filename='assignments.xlsx')


@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(PROCESSED_FOLDER, filename)
    return send_file(file_path, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)