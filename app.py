from flask import Flask, render_template, request, redirect, url_for, jsonify, abort, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'  # 請改成安全的隨機字串

db = SQLAlchemy(app)


class User(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(50), unique=True, nullable=False)
	password_hash = db.Column(db.String(128), nullable=False)
	posts = db.relationship('Post', backref='user', lazy=True)

	def set_password(self, password):
		self.password_hash = generate_password_hash(password)

	def check_password(self, password):
		return check_password_hash(self.password_hash, password)

class Post(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	title = db.Column(db.String(100), nullable=False)
	author = db.Column(db.String(50), nullable=False)
	content = db.Column(db.Text, nullable=False)
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

	def to_dict(self):
		return {
			'id': self.id,
			'title': self.title,
			'author': self.author,
			'content': self.content,
			'user_id': self.user_id
		}



# RESTful APIs
@app.route('/api/posts', methods=['POST'])
def api_create_post():
	data = request.get_json()
	if not data or not all(k in data for k in ('title', 'author', 'content')):
		abort(400)
	post = Post(title=data['title'], author=data['author'], content=data['content'])
	db.session.add(post)
	db.session.commit()
	return jsonify(post.to_dict()), 201

@app.route('/api/posts/<int:post_id>', methods=['GET'])
def api_read_post(post_id):
	post = Post.query.get_or_404(post_id)
	return jsonify(post.to_dict())

@app.route('/api/posts/<int:post_id>', methods=['PUT'])
def api_update_post(post_id):
	post = Post.query.get_or_404(post_id)
	data = request.get_json()
	for field in ['title', 'author', 'content']:
		if field in data:
			setattr(post, field, data[field])
	db.session.commit()
	return jsonify(post.to_dict())

@app.route('/api/posts/<int:post_id>', methods=['DELETE'])
def api_delete_post(post_id):
	post = Post.query.get_or_404(post_id)
	db.session.delete(post)
	db.session.commit()
	return '', 204

# 前端頁面
@app.route('/')
def index():
	posts = Post.query.order_by(Post.id.desc()).all()
	return render_template('index.html', posts=posts)

@app.route('/post/<int:post_id>')
def post_detail(post_id):
	post = Post.query.get_or_404(post_id)
	return render_template('post.html', post=post)


def login_required(f):
	from functools import wraps
	@wraps(f)
	def decorated_function(*args, **kwargs):
		if 'user_id' not in session:
			flash('請先登入')
			return redirect(url_for('login'))
		return f(*args, **kwargs)
	return decorated_function

@app.route('/new', methods=['GET', 'POST'])
@login_required
def new_post():
	if request.method == 'POST':
		title = request.form['title']
		author = request.form['author']
		content = request.form['content']
		user_id = session['user_id']
		post = Post(title=title, author=author, content=content, user_id=user_id)
		db.session.add(post)
		db.session.commit()
		return redirect(url_for('index'))
	return render_template('new_post.html')


@app.route('/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
	post = Post.query.get_or_404(post_id)
	if post.user_id != session['user_id']:
		flash('只能編輯自己創建的文章')
		return redirect(url_for('index'))
	if request.method == 'POST':
		post.title = request.form['title']
		post.author = request.form['author']
		post.content = request.form['content']
		db.session.commit()
		return redirect(url_for('post_detail', post_id=post.id))
	return render_template('edit_post.html', post=post)


@app.route('/delete/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
	post = Post.query.get_or_404(post_id)
	if post.user_id != session['user_id']:
		flash('只能刪除自己創建的文章')
		return redirect(url_for('index'))
	db.session.delete(post)
	db.session.commit()
	return redirect(url_for('index'))
# RESTful APIs
# ...existing code...

# 使用者註冊
@app.route('/register', methods=['GET', 'POST'])
def register():
	if request.method == 'POST':
		username = request.form['username']
		password = request.form['password']
		if User.query.filter_by(username=username).first():
			flash('使用者名稱已存在')
			return redirect(url_for('register'))
		user = User(username=username)
		user.set_password(password)
		db.session.add(user)
		db.session.commit()
		flash('註冊成功，請登入')
		return redirect(url_for('login'))
	return render_template('register.html')

# 使用者登入
@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		username = request.form['username']
		password = request.form['password']
		user = User.query.filter_by(username=username).first()
		if user and user.check_password(password):
			session['user_id'] = user.id
			session['username'] = user.username
			flash('登入成功')
			return redirect(url_for('index'))
		else:
			flash('帳號或密碼錯誤')
	return render_template('login.html')

# 使用者登出
@app.route('/logout')
def logout():
	session.clear()
	flash('已登出')
	return redirect(url_for('index'))

import os
if __name__ == '__main__':
	# 若 blog.db 已存在則刪除，確保新結構
	if os.path.exists('blog.db'):
		os.remove('blog.db')
	with app.app_context():
		db.create_all()
	app.run(debug=True)
