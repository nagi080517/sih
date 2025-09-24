#!/usr/bin/env python3
"""
Flask API for Railway Complaint Analyzer
Handles complaints via REST API with speech recognition support
"""

import os
import sys
import logging
import datetime
import traceback
import json
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

# ----------------- Logging -----------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

file_handler = logging.FileHandler("railway_api.log", encoding="utf-8")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# ----------------- Flask -----------------
app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app, resources={r"/*": {"origins": "*"}})

# ----------------- Import Components -----------------
MAIN_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_PATH = os.path.join(MAIN_DIR, "Backend")
if BACKEND_PATH not in sys.path:
    sys.path.insert(0, BACKEND_PATH)

# Import complaint handler
try:
    from Backend.railway import handle_complaint, classify_complaint
    logger.info("✅ Railway complaint handler loaded")
    complaint_handler_available = True
except Exception as e:
    logger.error(f"❌ Failed to load complaint handler: {e}")
    logger.error(traceback.format_exc())
    handle_complaint = None
    classify_complaint = None
    complaint_handler_available = False

# Import speech recognition (optional)
speech_function = None
speech_available = False
try:
    # Try to import your speech recognition function
    # from speech_recognition import recognize_speech_hindi
    logger.info("Speech recognition not implemented yet")
except Exception as e:
    logger.warning(f"Speech recognition not available: {e}")

# ----------------- Helper Functions -----------------
def initialize_log_files():
    """Create empty log files if they don't exist."""
    log_files = ["chat_logs.json", "urgent_logs.json", "normal_logs.json"]
    for log_file in log_files:
        if not os.path.exists(log_file):
            with open(log_file, "w") as f:
                json.dump([], f)
            logger.info(f"Created {log_file}")

def get_complaint_stats():
    """Get complaint statistics for dashboard."""
    stats = {
        "total_complaints": 0,
        "urgent_complaints": 0,
        "normal_complaints": 0,
        "today_complaints": 0
    }
    
    # Count from chat logs
    if os.path.exists("chat_logs.json"):
        try:
            with open("chat_logs.json", "r") as f:
                chat_logs = json.load(f)
                stats["total_complaints"] = len(chat_logs)
                
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                for log in chat_logs:
                    if log.get("urgent"):
                        stats["urgent_complaints"] += 1
                    else:
                        stats["normal_complaints"] += 1
                    
                    if log.get("timestamp", "").startswith(today):
                        stats["today_complaints"] += 1
        except:
            pass
    
    return stats

# ----------------- Routes -----------------

@app.route("/")
def home():
    """Serve the Railway Complaint UI"""
    try:
        return send_file("index.html")
    except:
        return jsonify({
            "message": "Railway Complaint Analyzer API",
            "status": "running",
            "endpoints": [
                "/api/health",
                "/api/complaint", 
                "/api/query",
                "/api/stats",
                "/api/logs"
            ]
        })


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check with system status"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "features": {
            "complaint_handler": complaint_handler_available,
            "speech_available": speech_available
        },
        "version": "1.0.0"
    })


@app.route("/api/complaint", methods=["POST"])
def complaint_api():
    """Handle passenger complaints"""
    if not complaint_handler_available:
        return jsonify({
            "success": False, 
            "error": "Complaint handler not loaded"
        }), 500

    try:
        data = request.get_json()
        if not data or "complaint" not in data:
            return jsonify({
                "success": False, 
                "error": "Missing 'complaint' field"
            }), 400

        complaint_text = data["complaint"].strip()
        if not complaint_text:
            return jsonify({
                "success": False, 
                "error": "Empty complaint"
            }), 400

        logger.info(f"📩 New complaint: {complaint_text[:100]}...")
        
        # Get classification first
        classification = classify_complaint(complaint_text)
        
        # Process the complaint (this will also handle logging)
        ai_response = handle_complaint(complaint_text)
        
        logger.info(f"✅ Complaint processed successfully")
        
        return jsonify({
            "success": True,
            "data": {
                "response": ai_response,
                "urgent": classification["urgent"],
                "reason": classification["reason"]
            },
            "timestamp": datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"⚠️ Complaint API error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False, 
            "error": str(e)
        }), 500


@app.route("/api/query", methods=["POST"])
def query_api():
    """General query endpoint (alias for complaint)"""
    return complaint_api()


@app.route("/api/speech", methods=["POST"])
def speech_recognition_api():
    """Handle speech recognition for complaints"""
    if not speech_available:
        return jsonify({
            "success": False,
            "error": "Speech recognition not available"
        }), 501

    try:
        # This would implement speech recognition
        # For now, return a placeholder response
        return jsonify({
            "success": False,
            "error": "Speech recognition not implemented yet"
        }), 501
        
    except Exception as e:
        logger.error(f"⚠️ Speech recognition error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/test-speech", methods=["GET"])
def test_speech():
    """Test speech recognition system"""
    return jsonify({
        "success": True,
        "status": {
            "speech_available": speech_available,
            "function_loaded": speech_function is not None,
            "function_callable": callable(speech_function),
            "backend_path_exists": os.path.exists(BACKEND_PATH),
            "audio_libraries": {
                "speech_recognition": "not available",
                "pyaudio": "not available", 
                "sounddevice": "not available"
            }
        }
    })


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Get complaint statistics"""
    try:
        stats = get_complaint_stats()
        return jsonify({
            "success": True,
            "data": stats,
            "timestamp": datetime.datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/logs/<log_type>", methods=["GET"])
def get_logs(log_type):
    """Get complaint logs"""
    log_files = {
        "chat": "chat_logs.json",
        "urgent": "urgent_logs.json", 
        "normal": "normal_logs.json"
    }
    
    if log_type not in log_files:
        return jsonify({
            "success": False,
            "error": "Invalid log type. Use: chat, urgent, or normal"
        }), 400
    
    try:
        log_file = log_files[log_type]
        if not os.path.exists(log_file):
            return jsonify({
                "success": True,
                "data": [],
                "message": f"No {log_type} logs found"
            })
        
        with open(log_file, "r") as f:
            logs = json.load(f)
            
        # Limit to last 50 entries and reverse for newest first
        logs = logs[-50:][::-1] if len(logs) > 50 else logs[::-1]
        
        return jsonify({
            "success": True,
            "data": logs,
            "count": len(logs),
            "log_type": log_type
        })
        
    except Exception as e:
        logger.error(f"Logs error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/emergency", methods=["POST"])
def emergency_alert():
    """Handle emergency complaints with immediate escalation"""
    try:
        data = request.get_json()
        complaint = data.get("complaint", "").strip()
        
        if not complaint:
            return jsonify({
                "success": False,
                "error": "Missing complaint text"
            }), 400
        
        # Log as urgent emergency
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        emergency_entry = {
            "timestamp": timestamp,
            "complaint": complaint,
            "type": "EMERGENCY",
            "status": "ESCALATED",
            "priority": "CRITICAL"
        }
        
        # Save to emergency log
        emergency_logs = []
        emergency_file = "emergency_logs.json"
        if os.path.exists(emergency_file):
            with open(emergency_file, "r") as f:
                try:
                    emergency_logs = json.load(f)
                except:
                    pass
        
        emergency_logs.append(emergency_entry)
        
        with open(emergency_file, "w") as f:
            json.dump(emergency_logs, f, indent=2)
        
        # Also process through normal complaint handler
        if complaint_handler_available:
            classification = classify_complaint(complaint)
            response = handle_complaint(complaint)
        else:
            response = "Emergency complaint received and escalated to railway authorities immediately."
            classification = {"urgent": True, "reason": "emergency"}
        
        logger.critical(f"🚨 EMERGENCY COMPLAINT: {complaint}")
        
        return jsonify({
            "success": True,
            "data": {
                "response": response,
                "urgent": True,
                "reason": "emergency"
            },
            "alert": "Emergency complaint escalated to authorities",
            "reference_id": f"EMR-{timestamp.replace(' ', '-').replace(':', '')}"
        })
        
    except Exception as e:
        logger.error(f"Emergency API error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ----------------- Error Handlers -----------------

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "Endpoint not found",
        "available_endpoints": [
            "/api/health",
            "/api/complaint",
            "/api/query", 
            "/api/stats",
            "/api/logs/<type>",
            "/api/emergency"
        ]
    }), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500


# ----------------- Main -----------------
def main():
    logger.info("🚆 Starting Railway Complaint Analyzer Flask API server...")
    logger.info(f"Backend path: {BACKEND_PATH}")
    logger.info(f"Complaint handler: {'✅ Available' if complaint_handler_available else '❌ Not available'}")
    logger.info(f"Speech recognition: {'✅ Available' if speech_available else '❌ Not available'}")
    
    # Initialize log files
    initialize_log_files()
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)


if __name__ == "__main__":
    main()