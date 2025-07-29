import datetime
from flask import Flask, abort, render_template, redirect, url_for, flash, request, session
from flask_bootstrap import Bootstrap5
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, Boolean, DateTime
from werkzeug.security import generate_password_hash, check_password_hash
from forms import *
import os
from dotenv import load_dotenv
import smtplib
import random

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_KEY')
Bootstrap5(app)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)

class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_URL', 'sqlite:///lists.db')
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lists.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)

class List(db.Model):
    __tablename__ = 'lists'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey('users.id'), nullable=True)
    author = relationship('User', back_populates='lists')
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    todos = relationship('ToDo', back_populates='parent')
    saved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

class ToDo(db.Model):
    __tablename__ = 'todos'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content: Mapped[str] = mapped_column(String(250), nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    display_due_date: Mapped[str] = mapped_column(String(250), nullable=True)
    done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    overdue: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    list_id: Mapped[int] = mapped_column(Integer, db.ForeignKey('lists.id'), nullable=False)
    parent = relationship('List', back_populates='todos')

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(100))
    lists = relationship('List', back_populates='author')

with app.app_context():
    db.create_all()

def generate_reset_code():
    return random.randint(100000, 999999)

def db_add(obj:object):
    db.session.add(obj)
    db.session.commit()

def db_delete(obj:object):
    db.session.delete(obj)
    db.session.commit()

def create_local_list():
    while True:
        title = f'local{random.randint(0, 999999999)}'
        if not db.session.execute(db.select(List).where(List.title == title)).scalar():
            lst = List(title=title)
            db_add(lst)
            db_add(ToDo(content='My First ToDo', list_id=lst.id))
            return lst.id

def add_todo(content, list_id):
    x = False
    for todo in db.session.execute(db.select(ToDo).where(ToDo.content == content)).scalars().all():
        if list_id == todo.list_id:
            flash('Please choose a different task name.')
            x = True
    if not x:
        db_add(ToDo(content=content, list_id=list_id))

def check_overdue(lst):
    for task in lst.todos:
        if task.due_date is not None:
            if datetime.datetime.now() > task.due_date:
                task.overdue = True
            else:
                task.overdue = False
    db.session.commit()

def check_right_user(list_id):
    pass

my_globals = []

@app.route('/', methods=['GET', 'POST'])
@app.route('/<new>', methods=['GET', 'POST'])
def home(new=False):
    if 'local_list_id' not in session or db.session.get(List, session['local_list_id']) is None:
        session['local_list_id'] = create_local_list()

    if new:
        session['local_list_id'] = create_local_list()
        return redirect(url_for('home'))

    if request.method == 'POST':
        if request.form.get('content') is not None:
            add_todo(request.form.get('content'), session['local_list_id'])
        else:
            edit_todo = db.session.get(ToDo, request.form.get('toggle'))
            edit_todo.done = not edit_todo.done
            db.session.commit()
        return redirect(url_for('home'))

    current_list = db.session.get(List, session['local_list_id'])
    check_overdue(current_list)
    return render_template('index.html', current_user=current_user, list=current_list, index_type=0)

@app.route('/<int:_id>', methods=['GET', 'POST'])
def display_list(_id):
    current_list = db.session.get(List, _id)
    check_right_user(_id)

    if request.method == 'POST':
        if request.form.get('content') is not None:
            add_todo(request.form.get('content'), current_list.id)
        else:
            edit_todo = db.session.get(ToDo, request.form.get('toggle'))
            if edit_todo.done:
                edit_todo.done = False
            else:
                edit_todo.done = True
            db.session.commit()
        return redirect(url_for('home'))

    check_overdue(current_list)
    return render_template('index.html', current_user=current_user, list=current_list, index_type=1)

@app.route('/add_date/<int:list_id>/<int:todo_id>/<int:index_type>', methods=['GET', 'POST'])
def add_date(list_id, todo_id, index_type):
    form = DateForm()
    check_right_user(list_id)

    if request.method == 'POST':
        db.session.get(ToDo, todo_id).due_date = form.date.data
        db.session.get(ToDo, todo_id).display_due_date = form.date.data.strftime('%b %d, %Y')
        db.session.commit()

        if index_type == 0:
            return redirect(url_for('home'))
        else:
            return redirect(url_for('display_list', _id=list_id))

    return render_template('index.html', form=form, todo_id=todo_id, list=db.session.get(List, list_id), index_type=index_type)

@app.route('/add/<int:list_id>', methods=['GET', 'POST'])
def add(list_id):
    check_right_user(list_id)
    form = AddListForm()

    if not current_user.is_authenticated:
        flash('Login in order to save this list')
        return redirect(url_for('login', save_list_id=list_id))

    if form.validate_on_submit():
        lst = db.session.get(List, list_id)
        for user_list in db.session.execute(db.select(List).where(List.author_id == current_user.id)).scalars().all():
            if form.title.data == user_list.title:
                flash('Pick a unique name from your current lists.')
                return redirect(url_for('add', list_id=list_id))
        lst.title = form.title.data
        lst.author_id = current_user.id
        lst.saved = True
        db.session.commit()
        return redirect(url_for('display_list', _id=list_id))

    return render_template('add.html', form=form)

@app.route('/delete/<x>/<int:_id>', methods=['GET', 'POST'])
def delete(x, _id):
    if x == 'todo':
        check_right_user(db.session.get(List, db.session.get(List, db.session.get(ToDo, _id).list_id)))
        db_delete(db.session.get(ToDo, _id))
        return redirect(url_for('home'))
    else:
        check_right_user(_id)
        form = DeleteForm()
        lst = db.session.get(List, _id)

        if form.validate_on_submit():
            for task in lst.todos:
                db_delete(task)
            db_delete(lst)
            return redirect(url_for('home', new=True))

    return render_template('delete.html', list=lst, form=form)

@app.route('/register', methods=['GET', 'POST'])
@app.route('/register/<int:save_list_id>', methods=['GET', 'POST'])
def register(save_list_id=None):
    global login_redirect
    login_redirect = [False]
    form = RegisterForm()

    if form.validate_on_submit():
        result = db.session.execute(db.select(User).where(User.email == form.email.data))
        user = result.scalar()

        if user:
            flash("You've already signed up with that email, log in instead!")
            login_redirect = [True, form.email.data]
            return redirect(url_for('login', save_list_id=save_list_id))

        hash_and_salted_password = generate_password_hash(form.password.data, method='pbkdf2:sha256', salt_length=8)
        new_user = User(email=form.email.data, name=form.name.data, password=hash_and_salted_password)
        db_add(new_user)
        login_user(new_user)
        if save_list_id is not None:
            return redirect(url_for('add', list_id=save_list_id))
        return redirect(url_for('home'))

    return render_template('register.html', form=form, current_user=current_user, register_type=0, save_list_id=save_list_id)

@app.route('/login', methods=['GET', 'POST'])
@app.route('/login/<int:save_list_id>', methods=['GET', 'POST'])
def login(save_list_id=None):
    global login_redirect

    try:
        if not login_redirect[0]:
            form = LoginForm()
        else:
            form = LoginForm(email=login_redirect[1])
    except NameError:
        form = LoginForm()

    if form.validate_on_submit():
        password = form.password.data
        result = db.session.execute(db.select(User).where(User.email == form.email.data))
        user = result.scalar()

        if not user:
            flash('That email does not exist, please try again.')
            return redirect(url_for('login', save_list_id=save_list_id))

        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login', save_list_id=save_list_id))

        else:
            login_user(user)
            if save_list_id is not None:
                return redirect(url_for('add', list_id=save_list_id))
            return redirect(url_for('home'))

    return render_template('register.html', form=form, current_user=current_user, register_type=1, save_list_id=save_list_id)

@app.route('/forgot_password/<int:n>', methods=['GET', 'POST'])
def forgot_password(n):
    if n == 0:
        form = EmailForm()
    else:
        form = ResetPasswordForm()

    if form.validate_on_submit():
        if n == 0:
            my_email = os.environ.get('EMAIL')
            password = os.environ.get('PASSWORD')
            to_email = form.email.data
            my_globals.append(to_email)

            session['reset_code'] = generate_reset_code()
            message = (f'Subject: Reset Your Password\n\nHi {db.session.execute(db.select(User).where(User.email == form.email.data)).scalar().name},\n'
                       f'We received a request to reset your password from the email {to_email}. Use the code below to complete the process:\n\n{session['reset_code']}\n\n'
                       f'If you did not request this, you can safely ignore this email.')

            with smtplib.SMTP('smtp.gmail.com', 587) as connection:
                connection.starttls()
                connection.login(user=my_email, password=password)
                connection.sendmail(from_addr=my_email, to_addrs=to_email, msg=message)

            return redirect(url_for('forgot_password', n=1))

        else:
            referer = request.headers.get("Referer")
            expected = url_for('forgot_password', n=0, _external=True)
            also_expected = url_for('forgot_password', n=1, _external=True)
            if referer != expected:
                if referer != also_expected:
                    abort(403)
            if form.code.data.strip() == str(session.get('reset_code')):
                if form.pass1.data == form.pass2.data:
                    current_user.password = generate_password_hash(form.pass1.data, method='pbkdf2:sha256', salt_length=8)
                    db.session.commit()

                    session.pop('reset_code', None)

                    user = db.session.execute(db.select(User).where(User.email == my_globals[0])).scalar()
                    my_globals.remove(my_globals[0])
                    login_user(user)
                    return redirect(url_for('home'))
                else:
                    flash('Passwords do not match.')
            else:
                flash('Invalid reset code.')

    return render_template('register.html', form=form, current_user=current_user, register_type=2, n=n)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home', new=True))

if __name__ == '__main__':
    app.run(debug=True)