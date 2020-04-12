from mymovielist import db
from flask_login import UserMixin
from mymovielist import login_manager
from flask import session



@login_manager.user_loader
def load_user(user_id):
    session['user_id'] = user_id
    return Users.query.get(int(user_id))


class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(60), unique=True, nullable=False)
    email = db.Column(db.String(60), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return f"User({self.username}, {self.email})"


class Movies(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plan_to_watch = db.Column(db.PickleType)
    completed = db.Column(db.PickleType)
    dropped = db.Column(db.PickleType)
    watching = db.Column(db.PickleType)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return f"Movies({self.id})"
