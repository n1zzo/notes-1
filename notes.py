#!/usr/bin/env python3
from flask import Flask, request, jsonify, abort, g
from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPBasicAuth
from passlib.apps import custom_app_context as pwd_context
import click

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)
auth = HTTPBasicAuth()


@click.group()
def cli():
    pass


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)

    def __iter__(self):
        yield 'id', self.id
        yield 'content', self.content


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), index=True)
    password_hash = db.Column(db.String(128))

    def hash_password(self, password):
        self.password_hash = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)

    def __iter__(self):
        yield 'id', self.id
        yield 'username', self.username


@auth.verify_password
def verify_password(username, password):
    user = User.query.filter_by(username=username).first()
    if not user or not user.verify_password(password):
        return False
    g.user = user
    return True


@app.route('/users')
def list_users():
    users = User.query.all()
    return jsonify([dict(user) for user in users])


@app.route('/users/<string:username>')
def get_user(username):
    user = User.query.filter_by(username=username).one_or_none()
    if user:
        return jsonify(dict(user))
    else:
        abort(404)


@app.route('/users', methods=['POST'])
# @auth.login_required
def register():
    username = request.json['username']
    password = request.json['password']

    if User.query.filter_by(username=username).one_or_none():
        app.logger.info('Username {} already taken'.format(username))
        abort(400)

    user = User(username=username)
    user.hash_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify(dict(user))


@app.route('/notes')
def list_notes():
    notes = Note.query.all()
    return jsonify([dict(note) for note in notes])


@app.route('/notes/<int:note_id>')
def show_note(note_id):
    note = Note.query.filter_by(id=note_id).one_or_none()
    if note:
        return jsonify(dict(note))
    else:
        abort(404)


@app.route('/notes', methods=['POST'])
@auth.login_required
def add_note():
    content = request.form['content']
    # author = g.user
    note = Note(content=content)

    db.session.add(note)
    db.session.commit()

    app.logger.info('Added note: ' + str(note))
    return jsonify(dict(note))


@cli.command('api')
@click.option('--debug', is_flag=True)
def run_api(debug):
    db.create_all()
    app.run(debug=debug)


if __name__ == '__main__':
    cli()
