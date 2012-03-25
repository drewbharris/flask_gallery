from flask import Flask, request, session, g, redirect, url_for, \
	 abort, render_template, flash
from werkzeug import secure_filename
# config.py must be in the same directory and have the proper fields filled out
import config, shutil
from datetime import date
import sys, subprocess, shlex, glob, Image, os, re, hashlib
from flaskext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
selected_config = config.dev
app.config.from_object(selected_config)
db = SQLAlchemy(app)




	
#VIEWS/CONTROLLERS
#
#

@app.route('/')
def index():
	session['title'] = None
	galleries = Gallery.query.all()
	return render_template('index.html', galleries=galleries)

@app.route('/gallery/<gallery_name>', defaults={'page': 1})
@app.route('/gallery/<gallery_name>/<int:page>')
def gallery(gallery_name, page):
	session['title'] = gallery_name
	photos = Photo.query.filter_by(gallery_name = gallery_name).order_by(Photo.file_name.asc()).all()
	if len(photos) == 1:
		last = True
	else:
		last = False
	date = Gallery.query.filter_by(gallery_name = gallery_name).first().creation_date
	paginated_photos = [photos[i:i+10] for i in range(0, len(photos), 10)]
	try:
		requested_photos = paginated_photos[page-1]
	except IndexError:
		flash('page not found')
		return redirect(url_for('gallery', gallery_name=gallery_name))	
	
	pages = len(paginated_photos)
	
	next = None
	prev = None
	
	if (pages > 1) and (page < pages):
		next = True
	if (pages > 1) and (page > 1):
		prev = True
			
		

	if photos == None:
		flash("Could not find specified gallery.")
		return redirect(url_for('index'))
	
	return render_template('gallery.html', gallery_name=gallery_name, photos=requested_photos, date=date, page=page, next=next, prev=prev, last=last)	

@app.route('/upload', methods=['GET', 'POST'])
def upload():
	session['title'] = "upload"
	#first find out if logged in
	if session['logged_in']:
		galleries = Gallery.query.all()
		if request.method == 'POST':
			f = request.files['photos']
			if not f:
				flash('please select a .zip file containing jpeg files')
				return render_template('upload.html', galleries=galleries)
			if request.form['gallery'] == 'new_gallery':
				gallery_name = request.form['new_gallery_name']
				if not gallery_name:
					flash('please enter a name for the new gallery')
					return render_template('upload.html', galleries=galleries)
			else:
				if request.form['new_gallery_name']:
					flash('please select either an existing new gallery or the \'new gallery\' option')
					return render_template('upload.html', galleries=galleries)
				else:
					gallery_name = request.form['gallery']	
			if not Gallery.query.filter_by(gallery_name=gallery_name).first():
				todays_date = date.today().strftime("%d.%m.%Y")
				db.session.add(Gallery(gallery_name, todays_date))
			zip_filename = os.path.join(selected_config.BASE_DIR,'temp/',secure_filename(f.filename))
			f.save(zip_filename)
			print gallery_name
			unpack_photos(zip_filename, gallery_name)
			return redirect(url_for('index'))
		else:
			return render_template('upload.html', galleries=galleries)
	else:
		return redirect(url_for('login'))
		
@app.route('/gallery/<gallery_name>/delete', methods=['GET', 'POST'])
def delete_gallery(gallery_name):
	if session['logged_in']:
		if request.method == 'POST':
			if request.form['delete'] == 'delete':
				Gallery.query.filter_by(gallery_name=gallery_name).delete()
				Photo.query.filter_by(gallery_name=gallery_name).delete()
				path = os.path.join(selected_config.BASE_DIR,'gallery/',gallery_name)
				shutil.rmtree(path)
				flash(gallery_name+' deleted.')
				return redirect(url_for('index'))
			else:
				return redirect(url_for('gallery', gallery_name=gallery_name))
		else:
			return render_template('delete_gallery.html', gallery_name=gallery_name)
	else:
		flash('you must be logged in to do that')
		return redirect(url_for('login'))
		
@app.route('/gallery/<gallery_name>/<file_name>/delete', methods=['GET', 'POST'])
def delete_image(gallery_name, file_name):
	if session['logged_in']:
		if request.method == 'POST':
			if request.form['delete'] == 'delete':
				Photo.query.filter_by(gallery_name=gallery_name, file_name=file_name).delete()
				image_path = os.path.join(selected_config.BASE_DIR,'gallery/',gallery_name,file_name+'.jpg')
				thumbnail_path = os.path.join(selected_config.BASE_DIR,'gallery/',gallery_name,'thumbs/'+file_name+'_small.jpg')
				os.remove(image_path)
				os.remove(thumbnail_path)
				flash(file_name+' from '+gallery_name+' deleted.')
				return redirect(url_for('gallery', gallery_name=gallery_name))
			else:
				return redirect(url_for('gallery', gallery_name=gallery_name))
		else:
			return render_template('delete_file.html', gallery_name=gallery_name, file_name=file_name)
	else:
		flash('you must be logged in to do that')
		return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
	session['title'] = "login"
	if request.method == 'POST':
		if valid_login(request.form['username'], request.form['password']):
			#if successful login, set the username session variable and redirect to the index page
			session['logged_in'] = True
			flash('logged in')
			return redirect(url_for('index')) 
		else:
			flash('invalid login')
			return render_template('login.html')
	else:
		return render_template('login.html')
		
@app.route('/logout')
def logout():
	session['logged_in'] = False
	return redirect(url_for('index'))
	
#MODELS
#
#

class User(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(80), unique=True)
	hashed_password = db.Column(db.String(120), unique=True)

	def __init__(self, username, hashed_password):
		self.username = username
		self.hashed_password = hashed_password

	def __repr__(self):
		return '<User %r>' % self.username
		
class Gallery(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	gallery_name = db.Column(db.String(80), unique=True)
	creation_date = db.Column(db.String(120))

	def __init__(self, gallery_name, creation_date):
		self.gallery_name = gallery_name
		self.creation_date = creation_date

	def __repr__(self):
		return '<Gallery %r>' % self.gallery_name
		
class Photo(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	file_name = db.Column(db.String(80))
	gallery_name = db.Column(db.String(80))
	upload_date = db.Column(db.String(120))

	def __init__(self, file_name, gallery_name, upload_date):
		self.file_name = file_name
		self.gallery_name = gallery_name
		self.upload_date = upload_date

	def __repr__(self):
		return '<Photo %r>' % self.file_name
		
#USER FUNCTIONS
#
#

def valid_login(username, raw_password):
	#try the login against the set username and password
	user = User.query.filter_by(username=username, hashed_password=hash_password(raw_password)).first()
	if (user):
		return True
	else:
		return False
		
def unpack_photos(zip_filename, gallery_name):

	dest_dir=os.path.join(selected_config.BASE_DIR,'gallery/',gallery_name)
	dest_dir = dest_dir.encode('ascii')

	#create the output directory and thumbnails directory
	if not os.path.exists(dest_dir):
		os.makedirs(dest_dir)
	os.chmod(dest_dir, 0777)
	if not os.path.exists(os.path.join(dest_dir,'thumbs')):
		os.makedirs(os.path.join(dest_dir,'thumbs'))
	os.chmod(os.path.join(dest_dir,'thumbs'),0777)
	
	#use OS unzip command to unzip all .jpg files from the source zipfile to the destination
	string = 'unzip -n '+zip_filename+' *.jpg -d "'+dest_dir+'"'

	subprocess.call(shlex.split(string))
	
	#delete the uploaded zip file
	os.remove(zip_filename)
	
	#list all .jpg files in the output directory
	path = dest_dir+'/*.jpg'
	path = path.encode('ascii')
	extracted_files=glob.glob(path)

	#set the thumbnail bounds
	size = 600, 2000
	album_thumb_size = 100, 500
	
	#get the upload date
	todays_date = date.today().strftime("%d.%m.%Y")
	
	#for each file extracted from the zip, generate a thumbnail, save it and insert the entry into the database
	first_photo = extracted_files[0]
	generate_album_thumbnail(dest_dir, first_photo, album_thumb_size)
	
	duplicates_detected = False
	
	for imagePath in extracted_files:
		
		#split filename from extension
		imageFile = os.path.basename(imagePath)
		file_name, ext = os.path.splitext(imageFile)
		
		if not Photo.query.filter_by(file_name = file_name, gallery_name=gallery_name).first():
			#if the photo doesn't already exist, in the db, make a thumbnail, save it and add the photo to the db
			generate_thumbnail(dest_dir, imagePath, size)
			db.session.add(Photo(file_name, gallery_name, todays_date))
			db.session.commit()
		else:
			duplicates_detected = True
	
	if duplicates_detected:
		flash('duplicate files were detected and were skipped')

	
def generate_thumbnail(path, imagePath, size):
	
	#split the filename from its extension
	filename_long = os.path.basename(imagePath)
	filename, ext = os.path.splitext(filename_long)
	
	#open the image, create the thumbnail and save it
	image=Image.open(imagePath)
	image.thumbnail(size, Image.ANTIALIAS)
	dest_path = path+'/thumbs/'+filename+'_small.jpg'
	dest_path = dest_path.encode('ascii')
	image.save(dest_path)
	
def generate_album_thumbnail(path, imagePath, size):
		
	#open the image, create the thumbnail and save it
	image=Image.open(imagePath)
	image.thumbnail(size, Image.ANTIALIAS)
	dest_path = path+'/thumbs/album_thumbnail.jpg'
	dest_path = dest_path.encode('ascii')
	image.save(dest_path)
	
def hash_password(raw_password):
	return hashlib.sha224(raw_password).hexdigest()

	
#SYSTEM FUNCTIONS
#
#

if __name__ == '__main__':
	app.run()


