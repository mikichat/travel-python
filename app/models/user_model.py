from flask_login import UserMixin
from database import get_db_connection

class User(UserMixin):
    def __init__(self, id, username, email, password):
        self.id = id
        self.username = username
        self.email = email
        self.password = password

    @staticmethod
    def get(user_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, email, password FROM users WHERE id = ?', (user_id,))
        user_data = cursor.fetchone()
        conn.close()
        if user_data:
            return User(id=user_data['id'], username=user_data['username'], email=user_data['email'], password=user_data['password'])
        return None
