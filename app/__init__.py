#===========================================================
# YOUR PROJECT TITLE HERE
# YOUR NAME HERE
#-----------------------------------------------------------
# BRIEF DESCRIPTION OF YOUR PROJECT HERE
#===========================================================


from flask import Flask, render_template, request, flash, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
import html

from app.helpers.session import init_session
from app.helpers.db      import connect_db
from app.helpers.errors  import init_error, not_found_error
from app.helpers.logging import init_logging
from app.helpers.auth    import login_required
from app.helpers.time    import init_datetime, utc_timestamp, utc_timestamp_now


# Create the app
app = Flask(__name__)

# Configure app
init_session(app)   # Setup a session for messages, etc.
init_logging(app)   # Log requests
init_error(app)     # Handle errors and exceptions
init_datetime(app)  # Handle UTC dates in timestamps


#-----------------------------------------------------------
# Home page route
#-----------------------------------------------------------
@app.get("/")
def index():
    with connect_db() as client:
        # Get all the things from the DB
        sql = """
            SELECT planes.id,
                   planes.name,
                   users.name AS owner

            FROM planes
            JOIN users ON planes.user_id = users.id

            ORDER BY planes.name ASC
        """
        params=[]
        result = client.execute(sql, params)
        planes = result.rows

        # And show them on the page
        return render_template("pages/home.jinja", planes=planes)

#-----------------------------------------------------------
# Planes page route - Show all the planes, and new plane form
#-----------------------------------------------------------
@app.get("/planes/")
def show_all_things():
    with connect_db() as client:
        # Get all the things from the DB
        sql = """
            SELECT planes.id,
                   planes.name,
                   users.name AS owner

            FROM planes
            JOIN users ON planes.user_id = users.id

            ORDER BY planes.name ASC
        """
        params=[]
        result = client.execute(sql, params)
        planes = result.rows

        # And show them on the page
        return render_template("pages/planes.jinja", planes=planes)


#-----------------------------------------------------------
# Thing page route - Show details of a single thing
#-----------------------------------------------------------
@app.get("/thing/<int:id>")
def show_one_thing(id):
    with connect_db() as client:
        # Get the thing details from the DB, including the owner info
        sql = """
            SELECT things.id,
                   things.name,
                   things.price,
                   things.user_id,
                   users.name AS owner

            FROM things
            JOIN users ON things.user_id = users.id

            WHERE things.id=?
        """
        params = [id]
        result = client.execute(sql, params)

        # Did we get a result?
        if result.rows:
            # yes, so show it on the page
            thing = result.rows[0]
            return render_template("pages/thing.jinja", thing=thing)

        else:
            # No, so show error
            return not_found_error()
        
#-----------------------------------------------------------
# Plane page route
#-----------------------------------------------------------
@app.get("/plane/<int:id>")
def plane(id):
    with connect_db() as client:
     # Get the thing details from the DB, including the owner info
        sql = """
            SELECT planes.id,
                   planes.name,
                   planes.description,
                   planes.suggested_player_level,
                   planes.user_id,
                   users.name AS owner

            FROM planes
            JOIN users ON planes.user_id = users.id

            WHERE planes.id=?
               """
        params = [id]   
        result = client.execute(sql, params)
        # Did we get a result?
        if result.rows:
            # yes, so show it on the page
            plane = result.rows[0]

        else:
            # No, so show error
            return not_found_error()
        sql = """
            SELECT planes.id,
                   enemies.id,
                   enemies.name,
                   enemies.type,
                   enemies.size,
                   enemies.challenge_rating,
                   enemies.plane_id,
                   enemies.user_id,
                   users.name AS owner

            FROM enemies
            JOIN planes ON enemies.plane_id = planes.id
            JOIN users ON enemies.user_id = users.id

            WHERE enemies.plane_id=? AND enemies.user_id=?
        """
        params = [id, session["user_id"]]
        result = client.execute(sql, params)
        enemies = result.rows
        return render_template("pages/plane.jinja", plane=plane, enemies=enemies)

#-----------------------------------------------------------
# Enemy info page route
#-----------------------------------------------------------
@app.get("/enemy_info/")
def enemy_info():
    return render_template("pages/enemy_info.jinja")


#-----------------------------------------------------------
# Route for showing the form to add a new plane
# - Restricted to logged in users
#-----------------------------------------------------------
@app.get("/plane_form")
@login_required
def plane_form():
    # Show the form to add a new plane
    return render_template("pages/plane_form.jinja")

#-----------------------------------------------------------
# Route for adding a thing, using data posted from a form
# - Restricted to logged in users
#-----------------------------------------------------------
@app.post("/add_plane")
@login_required
def add_a_plane():
    # Get the data from the form
    name  = request.form.get("name")
    description = request.form.get("description")
    suggested_player_level = request.form.get("suggested_player_level")

    # Sanitise the text inputs
    name = html.escape(name)

    # Get the user id from the session
    user_id = session["user_id"]

    with connect_db() as client:
        # Add the thing to the DB
        sql = "INSERT INTO planes (name, description, suggested_player_level, user_id) VALUES (?, ?, ?, ?)"
        params = [name, description, suggested_player_level, user_id]
        client.execute(sql, params)

        # Go back to the home page
        flash(f"Plane: '{name}' created", "success")
        return redirect("/")


#-----------------------------------------------------------
# Route for deleting a thing, Id given in the route
# - Restricted to logged in users
#-----------------------------------------------------------
@app.get("/delete/<int:id>")
@login_required
def delete_a_thing(id):
    # Get the user id from the session
    user_id = session["user_id"]

    with connect_db() as client:
        # Delete the thing from the DB only if we own it
        sql = "DELETE FROM things WHERE id=? AND user_id=?"
        params = [id, user_id]
        client.execute(sql, params)

        # Go back to the home page
        flash("Thing deleted", "success")
        return redirect("/things")







#-----------------------------------------------------------
# User registration form route
#-----------------------------------------------------------
@app.get("/register")
def register_form():
    return render_template("pages/register.jinja")


#-----------------------------------------------------------
# User login form route
#-----------------------------------------------------------
@app.get("/login")
def login_form():
    return render_template("pages/login.jinja")


#-----------------------------------------------------------
# Route for adding a user when registration form submitted
#-----------------------------------------------------------
@app.post("/add-user")
def add_user():
    # Get the data from the form
    name = request.form.get("name")
    username = request.form.get("username")
    password = request.form.get("password")

    with connect_db() as client:
        # Attempt to find an existing record for that user
        sql = "SELECT * FROM users WHERE username = ?"
        params = [username]
        result = client.execute(sql, params)

        # No existing record found, so safe to add the user
        if not result.rows:
            # Sanitise the name
            name = html.escape(name)

            # Salt and hash the password
            hash = generate_password_hash(password)

            # Add the user to the users table
            sql = "INSERT INTO users (name, username, password_hash) VALUES (?, ?, ?)"
            params = [name, username, hash]
            client.execute(sql, params)

            # And let them know it was successful and they can login
            flash("Registration successful", "success")
            return redirect("/login")

        # Found an existing record, so prompt to try again
        flash("Username already exists. Try again...", "error")
        return redirect("/register")


#-----------------------------------------------------------
# Route for processing a user login
#-----------------------------------------------------------
@app.post("/login-user")
def login_user():
    # Get the login form data
    username = request.form.get("username")
    password = request.form.get("password")

    with connect_db() as client:
        # Attempt to find a record for that user
        sql = "SELECT * FROM users WHERE username = ?"
        params = [username]
        result = client.execute(sql, params)

        # Did we find a record?
        if result.rows:
            # Yes, so check password
            user = result.rows[0]
            hash = user["password_hash"]

            # Hash matches?
            if check_password_hash(hash, password):
                # Yes, so save info in the session
                session["user_id"]   = user["id"]
                session["user_name"] = user["name"]
                session["logged_in"] = True

                # And head back to the home page
                flash("Login successful", "success")
                return redirect("/")

        # Either username not found, or password was wrong
        flash("Invalid credentials", "error")
        return redirect("/login")


#-----------------------------------------------------------
# Route for processing a user logout
#-----------------------------------------------------------
@app.get("/logout")
def logout():
    # Clear the details from the session
    session.pop("user_id", None)
    session.pop("user_name", None)
    session.pop("logged_in", None)

    # And head back to the home page
    flash("Logged out successfully", "success")
    return redirect("/")

