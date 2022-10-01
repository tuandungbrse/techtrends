import sqlite3, logging, sys, os
from flask import Flask, jsonify, json, render_template, request, url_for, redirect, flash, Response
from werkzeug.exceptions import abort, HTTPException

from http import HTTPStatus

homepage_view = 0

# Function to get a database connection.
# This function connects to database with the name `database.db`
def get_db_connection():
    connection = sqlite3.connect('database.db')
    connection.row_factory = sqlite3.Row
    return connection


# Function to get a post using its ID
def get_post(post_id):
    connection = get_db_connection()
    post = connection.execute('SELECT * FROM posts WHERE id = ?',
                              (post_id,)).fetchone()
    connection.close()
    return post


# Function to count the number of posts in the database
def count_post():
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()
    post_count = cursor.execute('SELECT COUNT(id) FROM posts').fetchone()
    connection.close()
    return post_count[0]


# Function to count the total connection to the database
def count_db_connection():
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()
    db_connection_count = cursor.execute('SELECT SUM(article_view) FROM posts').fetchall()
    connection.close()
    db_connection_final_count = db_connection_count[0][0] + homepage_view
    return db_connection_final_count


# Function to increment database connection by 1 per article visit
def update_db_connection(post_id):
    connection = get_db_connection()
    cur = connection.cursor()
    cur.execute('UPDATE posts SET article_view = article_view + 1 WHERE id = ?',
                (post_id,)).fetchone()
    connection.commit()
    connection.close()


# Define the Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your secret key'

# Define the main route of the web application
@app.route('/')
def index():
    connection = get_db_connection()
    # Add connection count from homepage view
    global homepage_view
    homepage_view += 1
    posts = connection.execute('SELECT * FROM posts').fetchall()
    connection.close()
    return render_template('index.html', posts=posts)


@app.route('/<int:post_id>')
def post(post_id):
    post = get_post(post_id)
    # Update the db connection
    update_db_connection(post_id)
    if post is None:
        # Log accessing non-existing article
        app.logger.error('A non-existing article was accessed! "404"')
        return render_template('404.html'), 404
    else:
        # Log accessing existing article
        app.logger.info('Article ' + '"' + post['title'] + '"' + ' retrieved!')
        return render_template('post.html', post=post)


# Define the About Us page
@app.route('/about')
def about():
    # Log accessing About Us page
    app.logger.info('"About Us" page was retrieved!')
    return render_template('about.html')


# Define the post creation functionality
@app.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('Title is required!')
        else:
            connection = get_db_connection()
            connection.execute('INSERT INTO posts (title, content, article_view ) VALUES (?, ?, ?)',
                               (title, content, '0'))
            connection.commit()
            connection.close()

            # Log newly created article
            app.logger.info('A new article ' + '"' + title + '"' + ' was created!')
            return redirect(url_for('index'))

    return render_template('create.html')


# Define the Healthcheck endpoint
@app.route('/healthz')
def healthz():
    try:
        connection = get_db_connection()
        connection.execute('SELECT * FROM posts').fetchall()
        response = app.response_class(
            response=json.dumps({"result": "OK - healthy"}),
            status=200,
            mimetype='application/json'
        )
    except sqlite3.OperationalError as err:
        response = app.response_class(
            response=json.dumps({"result": "ERROR - unhealthy"}),
            status=500,
            mimetype='application/json'
        )
    return response

# Define the metrics endpoint
@app.route('/metrics')
def metrics():
    response = app.response_class(
        response=json.dumps({"db_connection_count": count_db_connection(), "post_count": count_post()}),
        status=200,
        mimetype='application/json'
    )
    return response


# start the application on port 3111
if __name__ == "__main__":
    loglevel = os.getenv("LOGLEVEL", "DEBUG").upper()
    loglevel = (
        getattr(logging, loglevel)
        if loglevel in ["CRITICAL", "DEBUG", "ERROR", "INFO", "WARNING", ]
        else logging.DEBUG
    )

    # Set logger to handle STDOUT and STDERR
    stdout_handler = logging.StreamHandler(sys.stdout)
    stderr_handler = logging.StreamHandler(sys.stderr)
    handlers = [stderr_handler, stdout_handler]

    # Create the log file and format each log
    logging.basicConfig(
        format='%(levelname)s:%(name)s:%(asctime)s, %(message)s',
        level=loglevel,
        datefmt='%m-%d-%Y, %H:%M:%S',
        handlers=handlers
    )

    app.run(host='0.0.0.0', port='3111')
