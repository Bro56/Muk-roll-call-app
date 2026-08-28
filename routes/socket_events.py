from flask_socketio import emit, join_room, leave_room
from flask_login import current_user

def register_socket_events(socketio):
    @socketio.on('connect')
    def handle_connect():
        if current_user.is_authenticated:
            join_room(f"user_{current_user.id}")
            emit('connected', {'status': 'ok'})

    @socketio.on('join_course')
    def handle_join_course(data):
        course_id = data.get('course_id')
        if course_id and current_user.is_authenticated:
            join_room(f"course_{course_id}")

    @socketio.on('leave_course')
    def handle_leave_course(data):
        course_id = data.get('course_id')
        if course_id and current_user.is_authenticated:
            leave_room(f"course_{course_id}")

    @socketio.on('disconnect')
    def handle_disconnect():
        pass