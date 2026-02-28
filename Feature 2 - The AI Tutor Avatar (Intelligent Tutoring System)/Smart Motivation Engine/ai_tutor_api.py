import json
import os
from datetime import datetime
from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from motivation_engine import MotivationEngine, StudentMetrics, MessagePriority
from memory import ChatMemory
from classify import classify_mode
from rag_pipline import retrieve_chunks, generate_response
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app and SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize components
motivation_engine = MotivationEngine()
memory = ChatMemory()
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# Configure Gemini
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    raise ValueError("Set the GEMINI_API_KEY environment variable.")
genai.configure(api_key=gemini_api_key)
model_name = "gemini-2.0-flash"
client = genai.GenerativeModel(model_name)

# Track connected clients and student sessions
connected_clients = {}
student_sessions = {}  # student_id -> {last_activity, metrics, etc.}

def _dict_to_metrics(data: dict) -> StudentMetrics:
    """Convert dictionary to StudentMetrics object"""
    try:
        # Parse datetime fields if they're strings
        if "last_activity" in data and isinstance(data["last_activity"], str):
            data["last_activity"] = datetime.fromisoformat(data["last_activity"])
        
        # Ensure all required fields exist with defaults
        defaults = {
            "modules_completed": [],
            "modules_just_completed": [],
            "current_skill_levels": {},
            "previous_skill_levels": {},
            "skills_just_advanced": {},
            "overall_progress": 0.0,
            "learning_streak": 0,
            "time_since_last_activity": None
        }
        
        for key, default_value in defaults.items():
            if key not in data:
                data[key] = default_value
        
        return StudentMetrics(**data)
    except Exception as e:
        print(f"Error converting dict to metrics: {str(e)}")
        # Return minimal metrics object
        return StudentMetrics(
            student_id=data.get('student_id', 'unknown'),
            name=data.get('name', 'Unknown Student'),
            last_activity=datetime.now()
        )

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    client_id = request.sid
    print(f"Client connected: {client_id}")
    connected_clients[client_id] = socketio
    emit('connected', {'message': 'Connected to AI Tutor', 'client_id': client_id})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    client_id = request.sid
    print(f"Client disconnected: {client_id}")
    if client_id in connected_clients:
        # Clean up student session if it exists
        for student_id, session in list(student_sessions.items()):
            if session.get('client_id') == client_id:
                del student_sessions[student_id]
        del connected_clients[client_id]
    emit('disconnected', {'message': 'Disconnected from AI Tutor'})

@socketio.on('join_student_session')
def handle_join_student_session(data):
    """Join a session for a specific student"""
    student_id = data.get('student_id')
    client_id = request.sid
    
    if student_id:
        # Initialize student session if it doesn't exist
        if student_id not in student_sessions:
            student_sessions[student_id] = {
                'client_id': client_id,
                'last_activity': datetime.now(),
                'metrics': None,
                'memory': ChatMemory()
            }
        
        join_room(student_id)
        print(f"Client {client_id} joined session for student {student_id}")
        emit('session_joined', {'student_id': student_id, 'message': f'Joined session for student {student_id}'})

@socketio.on('leave_student_session')
def handle_leave_student_session(data):
    """Leave a session for a specific student"""
    student_id = data.get('student_id')
    client_id = request.sid
    
    if student_id and student_id in student_sessions:
        leave_room(student_id)
        print(f"Client {client_id} left session for student {student_id}")
        emit('session_left', {'student_id': student_id, 'message': f'Left session for student {student_id}'})

@socketio.on('update_student_metrics')
def handle_update_student_metrics(data):
    """Update student metrics and process for motivational messages"""
    try:
        student_id = data.get('student_id')
        
        if not student_id or student_id not in student_sessions:
            emit('error', {'message': 'Student session not found'})
            return
        
        # Update student metrics
        metrics = _dict_to_metrics(data)
        student_sessions[student_id]['metrics'] = metrics
        student_sessions[student_id]['last_activity'] = datetime.now()
        
        # Process student metrics for motivational messages
        messages = motivation_engine.process_student(metrics)
        
        # Send motivational messages if any
        for msg in messages:
            motivational_response = {
                "type": "motivation",
                "trigger": msg.trigger_type.value,
                "priority": msg.priority.value,
                "content": msg.message,
                "timestamp": datetime.now().isoformat()
            }
            
            emit('motivation_message', motivational_response, room=student_id)
            print(f"Sent motivation message to student {student_id}: {msg.trigger_type.value}")
        
        # Confirm metrics update
        emit('metrics_updated', {
            'student_id': student_id,
            'message': 'Student metrics updated successfully',
            'motivation_messages_count': len(messages)
        })
        
    except Exception as e:
        print(f"Error updating student metrics: {str(e)}")
        emit('error', {'message': 'Failed to update student metrics', 'error': str(e)})

@socketio.on('student_message')
def handle_student_message(data):
    """Handle student messages for RAG-based responses"""
    try:
        student_id = data.get('student_id')
        message_text = data.get('message')
        
        if not student_id or student_id not in student_sessions:
            emit('error', {'message': 'Student session not found'})
            return
        
        if not message_text:
            emit('error', {'message': 'Empty message received'})
            return
        
        # Update session activity
        student_sessions[student_id]['last_activity'] = datetime.now()
        
        # Get student memory
        memory = student_sessions[student_id]['memory']
        
        # Classify the message mode
        mode = classify_mode(message_text)
        print(f"Classified message from {student_id} as: {mode}")
        
        # Retrieve context chunks if needed
        context_chunks = None
        if mode == "Tutor mode":
            context_chunks = retrieve_chunks(message_text, "educational_materials", embedder=embedder)
        elif mode == "FAQs mode":
            context_chunks = retrieve_chunks(message_text, "FAQs", embedder=embedder)
        
        # Prepare memory text
        memory_text = "\n".join([f"{m['role']}: {m['content']}" for m in memory.get_all_messages()])
        
        # Add message to memory
        memory.add_message("student", message_text)
        
        # Generate response
        answer = generate_response(message_text, mode, context_chunks, memory_text)
        
        # Add response to memory
        memory.add_message("tutor", answer)
        
        # Send response
        response_data = {
            "type": "response",
            "mode": mode,
            "content": answer,
            "timestamp": datetime.now().isoformat()
        }
        
        emit('tutor_response', response_data, room=student_id)
        print(f"Sent response to student {student_id} in mode: {mode}")
        
    except Exception as e:
        print(f"Error processing student message: {str(e)}")
        emit('error', {'message': 'Failed to process student message', 'error': str(e)})

@socketio.on('get_conversation_history')
def handle_get_conversation_history(data):
    """Get conversation history for a student"""
    try:
        student_id = data.get('student_id')
        
        if not student_id or student_id not in student_sessions:
            emit('error', {'message': 'Student session not found'})
            return
        
        memory = student_sessions[student_id]['memory']
        history = memory.get_all_messages()
        
        emit('conversation_history', {
            'student_id': student_id,
            'history': history,
            'count': len(history)
        })
        
    except Exception as e:
        print(f"Error getting conversation history: {str(e)}")
        emit('error', {'message': 'Failed to get conversation history', 'error': str(e)})

@socketio.on('clear_conversation_history')
def handle_clear_conversation_history(data):
    """Clear conversation history for a student"""
    try:
        student_id = data.get('student_id')
        
        if not student_id or student_id not in student_sessions:
            emit('error', {'message': 'Student session not found'})
            return
        
        memory = student_sessions[student_id]['memory']
        memory.reset_memory()
        
        emit('conversation_cleared', {
            'student_id': student_id,
            'message': 'Conversation history cleared'
        })
        
    except Exception as e:
        print(f"Error clearing conversation history: {str(e)}")
        emit('error', {'message': 'Failed to clear conversation history', 'error': str(e)})

@socketio.on('health_check')
def handle_health_check():
    """Health check via WebSocket"""
    emit('health_status', {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'active_sessions': len(student_sessions),
        'connected_clients': len(connected_clients)
    })

if __name__ == "__main__":
    # Run the unified WebSocket server
    print("Starting AI Tutor WebSocket API...")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
