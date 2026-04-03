from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import re

app = Flask(__name__)
CORS(app)  # Allows our React Native app to communicate with this API

# 1. Load the trained ML Model
try:
    model = joblib.load('model/solidity_vuln_model.pkl')
    print("Model loaded successfully.")
except Exception as e:
    print(f"Error loading model: {e}")
    model = None

# 2. Preprocessing function (must match exactly what we did in training)
def clean_code(text):
    text = re.sub(r'//.*', '', text)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# 3. Explainable AI Logic
def analyze_code_logic(code):
    vulnerabilities = []
    explanation = []
    risk_level = "Low"

    # Rule-based explainability
    if "call.value" in code:
        vulnerabilities.append("Reentrancy")
        explanation.append("External call (call.value) detected before state update.")
        risk_level = "High"
    
    if "delegatecall" in code:
        vulnerabilities.append("Unsafe Delegatecall")
        explanation.append("Use of delegatecall can allow malicious contracts to alter state.")
        risk_level = "High"

    if "require" not in code and ("transfer" in code or "call" in code):
        vulnerabilities.append("Missing Access Control / Validation")
        explanation.append("State changing or fund transfer operations missing 'require' validation.")
        if risk_level != "High":
            risk_level = "Medium"

    if not vulnerabilities:
        explanation.append("Code appears to follow safe patterns based on current analysis.")

    return risk_level, vulnerabilities, " ".join(explanation)

# 4. API Endpoints

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "AI Smart Guard API is running!"}), 200

@app.route('/analyze', methods=['POST'])
def analyze():
    if not model:
        return jsonify({"error": "ML model is not loaded."}), 500

    data = request.get_json()
    
    if not data or 'code' not in data:
        return jsonify({"error": "No solidity code provided."}), 400

    raw_code = data['code']
    cleaned_code = clean_code(raw_code)

    # ML Prediction
    prediction = model.predict([cleaned_code])[0]
    probabilities = model.predict_proba([cleaned_code])[0]
    confidence_score = round(max(probabilities), 2)

    # Explainable AI Analysis
    risk_level, vulnerabilities, explanation = analyze_code_logic(raw_code)

    # Fallback to ML classification if rules miss it but ML catches it
    if prediction == 1 and "Reentrancy" not in vulnerabilities:
        vulnerabilities.append("Reentrancy (Detected by ML)")
        risk_level = "High"
    elif prediction == 2 and "Unsafe Delegatecall" not in vulnerabilities:
        vulnerabilities.append("Unsafe Delegatecall (Detected by ML)")
        risk_level = "High"

    # Response Object
    response = {
        "risk": risk_level,
        "vulnerabilities": vulnerabilities,
        "confidence": confidence_score,
        "explanation": explanation
    }

    return jsonify(response), 200

if __name__ == '__main__':
    # Run the Flask app on port 5000
    app.run(host='0.0.0.0', port=5000, debug=True)
