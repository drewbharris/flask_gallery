from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash
from werkzeug import secure_filename
import os, re
import sqlite3
from datetime import date
import sys
import subprocess
import shlex
import glob
import Image

#configuration
DATABASE = '/home/dbharris/webapps/gallery/gallery/db/photos.db'
DEBUG = True
SECRET_KEY = 'SZ\x85\xf96\x9f\x10\x0c\x02\'"\xe9\xa3\xbcS/\x9d\xc4\x05\x1c5\xd6*\xa2'
USERNAME = 'username'
PASSWORD = 'password'
BASE_DIR = '/home/dbharris/webapps/gallery/gallery/static'

#username/password are just tests now. will deploy with encryption when this is public

app = Flask(__name__)
app.config.from_object(__name__)
	
#VIEWS/CONTROLLERS
#
#

@app.route('/')
def index():
	session['title'] = None
	galleries_db = g.db.execute('select distinct gallery_name, creation_date from photos', [])
	galleries = [dict(gallery_name=row[0], creation_date=row[1]) for row in galleries_db.fetchall()]
	return render_template('index.html', galleries=galleries)

@app.route('/gallery/<gallery_name>')
def gallery(gallery_name):
	session['title'] = gallery_name
	gallery_photos_db = g.db.execute('select gallery_name, file_name from photos where gallery_name=?', [gallery_name])
	photos = [dict(gallery_name=row[0], file_name=row[1]) for row in gallery_photos_db.fetchall()]
	date_db = g.db.execute('select distinct creation_date from photos where gallery_name=?', [gallery_name])
	date = [dict(creation_date=row[0]) for row in date_db.fetchall()]
	if photos == None:
		flash("Could not find specified gallery.")
		return redirect(url_for('index'))
	return render_template('gallery.html', gallery_name=gallery_name, photos=photos, date=date)	

@app.route('/upload', methods=['GET', 'POST'])
def upload():
	session['title'] = "upload"
	#first find out if logged in
	if session['logged_in']:
		if request.method == 'POST':
			#
			f = request.files['photos']
			gallery_name = request.form['gallery_name']
			zip_filename = os.path.join(BASE_DIR,'temp/',secure_filename(f.filename))
			f.save(zip_filename)
			unpack_photos(zip_filename, gallery_name)
			return redirect(url_for('index'))
		else:
			return render_template('upload.html')
	else:
		return redirect(url_for('login'))
		
@app.route('/gallery/<gallery_name>/delete', methods=['GET', 'POST'])
def delete_gallery(gallery_name):
	if session['logged_in']:
		if request.method == 'POST':
			if request.form['delete']:
				#do the delete
				print "deleted"
			else:
				return redirect(url_for('gallery', gallery_name=gallery_name))
		else:
			render_template('delete_gallery.html', gallery_name=gallery_name)
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
		return render_template('login.html')
		
@app.route('/logout')
def logout():
	session['logged_in'] = False
	return redirect(url_for('index'))
		
#USER FUNCTIONS
#
#

def valid_login(username, password):
	#try the login against the set username and password
	if (username==app.config['USERNAME']) and (password==app.config['PASSWORD']):
		return True
	else:
		return False
		
def unpack_photos(zip_filename, gallery_name):
	#open the database connection
	db = get_connection()
	dest_dir=os.path.join(BASE_DIR,'gallery/',gallery_name)
	dest_dir = dest_dir.encode('ascii')

	#create the output directory and thumbnails directory
	os.makedirs(dest_dir)
	os.chmod(dest_dir, 0777)
	os.makedirs(os.path.join(dest_dir,'thumbs'))
	os.chmod(os.path.join(dest_dir,'thumbs'),0777)
	
	#use OS unzip command to unzip all .jpg files from the source zipfile to the destination
	string = 'unzip '+zip_filename+' *.jpg -d '+dest_dir

	subprocess.call(shlex.split(string))
	
	#delete the uploaded zip file
	os.remove(zip_filename)
	
	#list all .jpg files in the output directory
	path = dest_dir+'/*.jpg'
	path = path.encode('ascii')
	extracted_files=glob.glob(path)

	#set the thumbnail bounds
	size = 700, 2000
	
	#get the upload date
	today = date.today().strftime("%d.%m.%Y")
	
	#for each file extracted from the zip, generate a thumbnail, save it and insert the entry into the database
	for imagePath in extracted_files:
		generate_thumbnail(dest_dir, imagePath, size)
		imageFile = os.path.basename(imagePath)
		filename, ext = os.path.splitext(imageFile)
		db.execute('insert into photos (gallery_name, file_name, creation_date) values (?, ?, ?)', [gallery_name, filename, today])
		db.commit()
	
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
	
#SYSTEM FUNCTIONS
#
#

@app.before_request
def before_request():
	g.db = connect_db()
	
@app.teardown_request
def teardown_request(exception):
	g.db.close()
	
def get_connection():
    db = getattr(g, '_db', None)
    if db is None:
        db = g._db = connect_db()
    return db

def connect_db():
	return sqlite3.connect(app.config['DATABASE'])

if __name__ == '__main__':
	app.run()


