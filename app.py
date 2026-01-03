import sqlite3
import json
from flask import Flask, render_template, request, jsonify, g
import os

app = Flask(__name__)
DB_FILE = 'vAIdya.db'

# --- Database Setup ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_FILE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        # Patients Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                age INTEGER,
                sex TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Visits Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER,
                symptoms TEXT, -- JSON stored as text
                analysis_result TEXT, -- JSON stored as text
                locked_disease TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients (id)
            )
        ''')
        db.commit()

# --- Core Logic: Probabilistic Engine (Mock/Rule-based) ---
# In a real system, this would be a sophisticated ML model.
# Here, we use a dictionary mapping symptoms to diseases with weights.
# This serves the "Scientific Foundation" requirement of the prompt.

DISEASE_KNOWLEDGE_BASE = {
    "GERD": {
        "symptoms": ["heartburn", "acid reflux", "chest pain", "regurgitation", "difficulty swallowing"],
        "base_prob": 0.1,
        "risk_factors": ["obesity", "smoking"],
        "explanation": "Gastroesophageal Reflux Disease (GERD) is suggested by burning sensation in the chest and regurgitation.",
        "tests": ["Upper Endoscopy", "Esophageal pH monitoring"]
    },
    "Angina": {
        "symptoms": ["chest pain", "shortness of breath", "nausea", "fatigue", "dizziness"],
        "base_prob": 0.05,
        "risk_factors": ["age>45", "hypertension", "high cholesterol"],
        "explanation": "Symptoms overlap with cardiac issues. Chest pain combined with shortage of breath warrants investigation for Angina.",
        "tests": ["ECG", "Stress Test", "Coronary Angiography"]
    },
    "Common Cold": {
        "symptoms": ["runny nose", "sore throat", "cough", "sneezing", "mild fever"],
        "base_prob": 0.2,
        "risk_factors": [],
        "explanation": "Classic viral upper respiratory symptoms.",
        "tests": ["Physical Exam", "Rapid Strep Test (to rule out strep)"]
    },
    "Migraine": {
        "symptoms": ["headache", "nausea", "sensitivity to light", "sensitivity to sound", "throbbing"],
        "base_prob": 0.1,
        "risk_factors": ["family history", "female"],
        "explanation": "Unilateral throbbing headache with sensory sensitivity is characteristic of Migraine.",
        "tests": ["MRI (to rule out others)", "Neurological Exam"]
    },
    "Type 2 Diabetes (Early Warning)": {
        "symptoms": ["excessive thirst", "frequent urination", "hunger", "fatigue", "blurred vision"],
        "base_prob": 0.05,
        "risk_factors": ["obesity", "age>45", "sedentary"],
        "explanation": "Polydipsia (thirst) and polyuria (urination) are hallmark signs of high blood sugar.",
        "tests": ["HbA1c", "Fasting Plasma Glucose"]
    }
}

CARE_ROADMAPS = {
    "GERD": {
        "medication": ["Antacids", "H2 blockers", "Proton pump inhibitors (PPIs)"],
        "lifestyle": ["Avoid trigger foods (spicy, fatty)", "Eat smaller meals", "Wait 3 hours before lying down"],
        "diet": ["Low-acid foods", "Lean proteins", "Vegetables"],
        "monitoring": ["Monitor frequency of heartburn", "Watch for difficulty swallowing"]
    },
    "Angina": {
        "medication": ["Nitrates", "Aspirin", "Beta-blockers", "Statins"],
        "lifestyle": ["Stop smoking", "Stress management", "Cardiac rehabilitation"],
        "diet": ["Heart-healthy diet (low saturated fat, low sodium)"],
        "monitoring": ["Blood pressure reading", "Lipid profile check"]
    },
    "Common Cold": {
        "medication": ["Pain relievers", "Decongestants", "Cough suppressants"],
        "lifestyle": ["Rest", "Hydration"],
        "diet": ["Warm fluids", "Soup"],
        "monitoring": ["Monitor fever temperature", "Watch for worsening breath"]
    },
    "Migraine": {
        "medication": ["Pain relief", "Triptans", "Anti-nausea meds"],
        "lifestyle": ["Sleep hygiene", "Stress management", "Identify triggers"],
        "diet": ["Magnesium-rich foods", "Hydration"],
        "monitoring": ["Headache diary"]
    },
    "Type 2 Diabetes (Early Warning)": {
        "medication": ["Metformin (if prescribed)", "Insulin (if advanced)"],
        "lifestyle": ["Weight loss", "Regular exercise (150 mins/week)"],
        "diet": ["Low glycemic index foods", "Portion control"],
        "monitoring": ["Daily blood sugar monitoring", "Foot checks"]
    }
}

def calculate_probabilities(user_symptoms, user_age, user_sex):
    """
    Simple Bayesian-inspired probabilistic calculation.
    """
    scores = {}
    total_score = 0
    
    # Normalize inputs
    user_symptoms = [s.lower().strip() for s in user_symptoms]
    
    for disease, info in DISEASE_KNOWLEDGE_BASE.items():
        score = info['base_prob']
        match_count = 0
        
        # Symptom Matching
        for symptom in info['symptoms']:
            if any(s in symptom or symptom in s for s in user_symptoms):
                score += 0.15 # Bump for matching symptom
                match_count += 1
        
        # Risk Factor Analysis (Simple heuristic)
        if "age>45" in info['risk_factors'] and isinstance(user_age, int) and user_age > 45:
             score += 0.1
        
        if "female" in info['risk_factors'] and user_sex.lower() == 'female':
            score += 0.1
            
        scores[disease] = score
        total_score += score

    # Convert to percentages
    results = []
    if total_score > 0:
        for disease, score in scores.items():
            prob = int((score / total_score) * 100)
            if prob > 5: # Threshold to show
                results.append({
                    "name": disease,
                    "probability": prob,
                    "explanation": DISEASE_KNOWLEDGE_BASE[disease]["explanation"],
                    "suggested_tests": DISEASE_KNOWLEDGE_BASE[disease]["tests"]
                })
    
    # Sort by probability
    results.sort(key=lambda x: x['probability'], reverse=True)
    return results

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.json
    name = data.get('name')
    age = int(data.get('age', 0))
    sex = data.get('sex', '')
    symptoms = data.get('symptoms', []) # List of strings

    # Save patient if new (Simplified logic: always create new analysis context, link if name exists etc - keeping simple for now)
    # Ideally check if patient exists by name/dob.
    
    db = get_db()
    cursor = db.cursor()
    
    # Simple check for existing patient
    cursor.execute('SELECT id FROM patients WHERE name = ?', (name,))
    patient = cursor.fetchone()
    
    if not patient:
        cursor.execute('INSERT INTO patients (name, age, sex) VALUES (?, ?, ?)', (name, age, sex))
        patient_id = cursor.lastrowid
    else:
        patient_id = patient['id']
        # Update details? optional
    
    results = calculate_probabilities(symptoms, age, sex)
    
    # Log visit
    cursor.execute('INSERT INTO visits (patient_id, symptoms, analysis_result) VALUES (?, ?, ?)',
                   (patient_id, json.dumps(symptoms), json.dumps(results)))
    db.commit()
    
    return jsonify({"results": results, "patient_id": patient_id})

@app.route('/api/roadmap', methods=['POST'])
def roadmap():
    data = request.json
    disease = data.get('disease')
    patient_id = data.get('patient_id')
    
    roadmap_data = CARE_ROADMAPS.get(disease, {})
    
    # Update visit with the locked choice
    if patient_id:
        db = get_db()
        cursor = db.cursor()
        # Get latest visit for patient
        cursor.execute('SELECT id FROM visits WHERE patient_id = ? ORDER BY id DESC LIMIT 1', (patient_id,))
        visit = cursor.fetchone()
        if visit:
            cursor.execute('UPDATE visits SET locked_disease = ? WHERE id = ?', (disease, visit['id']))
            db.commit()

    return jsonify({"roadmap": roadmap_data})

if __name__ == '__main__':
    if not os.path.exists(DB_FILE):
        init_db()
    app.run(debug=True, port=5000)
