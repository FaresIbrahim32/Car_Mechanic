from flask import Flask, render_template, request, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate 
from dotenv import load_dotenv
from modes import GoogleMapsService
import os
load_dotenv()


# Initialize Flask app
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "supersecretkey"

# In your app.py, add this after other configurations
app.config['GOOGLE_MAPS_API_KEY'] = os.getenv('GOOGLE_MAPS_API_KEY')

# Initialize database and login manager
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"





class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    
    vehicles = db.relationship('Vehicle', backref='user', cascade="all, delete-orphan", lazy=True)
    tickets = db.relationship('Ticket', backref='user', cascade="all, delete-orphan", lazy=True)

class Vehicle(db.Model): 
    id = db.Column(db.Integer, primary_key=True)
    license_plate = db.Column(db.String(20), nullable=False, unique=True)
    vehicle_make = db.Column(db.String(50), nullable=False)
    vehicle_model = db.Column(db.String(50), nullable=False)
    vehicle_type = db.Column(db.String(30), nullable=False) 
    owner_name = db.Column(db.String(100), nullable=False)
    owner_number = db.Column(db.String(10), nullable=True) 
    registered_address = db.Column(db.String(1000), nullable=True)
    zip_code = db.Column(db.String(1000), nullable=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    issue = db.Column(db.String(1000), nullable=False)
    location = db.Column(db.String(1000), nullable=False)
    status = db.Column(db.String(10), nullable=False)
    formatted_address = db.Column(db.String(1000), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True) 
    vehicle = db.Column(db.String(100), nullable=False)  # String field only
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
def home():
    return render_template("home.html")

# Register route
@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if User.query.filter_by(username=username).first():
            return render_template("sign_up.html", error="Username already taken!")

        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")

        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("login"))
    
    return render_template("sign_up.html")

# Login route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("dashboard")) 
        else:
            return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")


@app.route('/dashboard')
@login_required
def dashboard():
    user_vehicles = Vehicle.query.filter_by(user_id=current_user.id).all()
    user_tickets = Ticket.query.filter_by(user_id=current_user.id).all()
    return render_template("dashboard.html", username=current_user.username,
                          user_vehicles=user_vehicles, user_tickets=user_tickets)

@app.route('/car', methods=['GET', 'POST'])
@login_required
def get_car():
    if request.method == "POST":
        # Get form data
        vehicle_type = request.form.get('vehicle_type')
        vehicle_make = request.form.get('vehicle_make')
        vehicle_model = request.form.get('vehicle_model')
        license_plate = request.form.get('license_plate')
        owner_name = request.form.get('owner_name')
        owner_number = request.form.get('owner_number')
        registered_address = request.form.get('registered_address')
        
        # Check if license plate already exists
        if Vehicle.query.filter_by(license_plate=license_plate).first():
            return render_template("car.html", error="License plate already registered!")
        
        # Create new vehicle
        new_vehicle = Vehicle(
            license_plate=license_plate,
            vehicle_make=vehicle_make,
            vehicle_model=vehicle_model,
            vehicle_type=vehicle_type,
            owner_name=owner_name,
            owner_number=owner_number,
            registered_address=registered_address,
            user_id=current_user.id
        )
        
        # Save to database
        try:
            db.session.add(new_vehicle)
            db.session.commit()
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            return render_template("car.html", error="Error registering vehicle. Please try again.")
    
    return render_template("car.html")


@app.route('/edit_car/<int:car_id>', methods=['POST','GET'])  
@login_required
def edit_car(car_id):
    vehicle = Vehicle.query.get_or_404(car_id)
    
    if vehicle.user_id != current_user.id:
        return redirect(url_for('dashboard'))
    
    if request.method == "POST":
        vehicle_type = request.form.get('vehicle_type')
        vehicle_make = request.form.get('vehicle_make')
        vehicle_model = request.form.get('vehicle_model')
        license_plate = request.form.get('license_plate')
        owner_name = request.form.get('owner_name')
        owner_number = request.form.get('owner_number')
        registered_address = request.form.get('registered_address')
        
        vehicle.vehicle_type = vehicle_type 
        vehicle.vehicle_make = vehicle_make 
        vehicle.vehicle_model = vehicle_model
        vehicle.license_plate = license_plate
        vehicle.owner_name = owner_name
        vehicle.owner_number = owner_number
        vehicle.registered_address= registered_address
        
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('edit_car.html',vehicle=vehicle)



@app.route('/delete_car/<int:car_id>',methods=['GET','POST'])
@login_required
def delete_car(car_id):
    car = Vehicle.query.get_or_404(car_id)
    
    # Check if user owns this ticket
    if car.user_id != current_user.id:
        return redirect(url_for('dashboard'))
    
    try:
        db.session.delete(car)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
    
    return redirect(url_for('dashboard'))
    


@app.route('/ticket', methods=['GET','POST'])
@login_required
def ticket():
    user_vehicles = Vehicle.query.filter_by(user_id=current_user.id).all()
    
    if request.method == "POST":
        issue = request.form.get('issue')
        location = request.form.get('location')
        vehicle = request.form.get('vehicle')
        
        if not user_vehicles:
            return render_template("ticket.html", 
                                 error="You must register a vehicle before creating a ticket.",
                                 user_vehicles=user_vehicles)
        
        if not issue or not location or not vehicle:
            return render_template("ticket.html", 
                                 error="Please fill in all required fields.",
                                 user_vehicles=user_vehicles)
        
        try:
            # Initialize Google Maps service
            maps_service = GoogleMapsService(app.config['GOOGLE_MAPS_API_KEY'])
            
            # Geocode the location
            geocode_result = maps_service.geocode_address(location)
            
            # Create ticket
            new_ticket = Ticket(
                issue=issue,
                location=location,
                vehicle=vehicle,
                status='Pending',
                user_id=current_user.id
            )
            
            # Add geocoded information if successful
            if geocode_result['success']:
                new_ticket.formatted_address = geocode_result['formatted_address']
                new_ticket.latitude = geocode_result['latitude']
                new_ticket.longitude = geocode_result['longitude']
            
            db.session.add(new_ticket)
            db.session.commit()
            
            # Redirect to mechanics page if geocoding was successful
            if geocode_result['success']:
                return redirect(url_for('nearby_mechanics', ticket_id=new_ticket.id))
            else:
                return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            return render_template("ticket.html", 
                                 error=f"Error creating your ticket: {str(e)}",
                                 user_vehicles=user_vehicles)
    
    return render_template("ticket.html", user_vehicles=user_vehicles)
    
@app.route('/edit_ticket/<int:ticket_id>', methods=['POST','GET'])  
@login_required
def edit_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Check if user owns this ticket
    if ticket.user_id != current_user.id:
        return redirect(url_for('dashboard'))
    
    # Get user's vehicles for the dropdown
    user_vehicles = Vehicle.query.filter_by(user_id=current_user.id).all()
    
    if request.method == "POST":
        issue = request.form.get('issue')
        location = request.form.get('location')
        vehicle = request.form.get('vehicle')
        
        # Validate required fields
        if not issue or not location or not vehicle:
            return render_template("edit_ticket.html", 
                                 ticket=ticket,
                                 user_vehicles=user_vehicles,
                                 error="Please fill in all required fields.")
        
        ticket.issue = issue 
        ticket.location = location
        ticket.vehicle = vehicle  # Update vehicle info
        
        try:
            db.session.commit()
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            return render_template("edit_ticket.html", 
                                 ticket=ticket,
                                 user_vehicles=user_vehicles,
                                 error="Error updating ticket. Please try again.")
    
    return render_template("edit_ticket.html", ticket=ticket, user_vehicles=user_vehicles)

# New route to mark ticket as completed
@app.route('/complete_ticket/<int:ticket_id>', methods=['POST'])
@login_required
def complete_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Check if user owns this ticket
    if ticket.user_id != current_user.id:
        return redirect(url_for('dashboard'))
    
    ticket.status = 'Completed'
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
    
    return redirect(url_for('dashboard'))

# Fixed: Added missing forward slash
@app.route('/delete_ticket/<int:ticket_id>', methods=['POST'])
@login_required
def delete_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Check if user owns this ticket
    if ticket.user_id != current_user.id:
        return redirect(url_for('dashboard'))
    
    try:
        db.session.delete(ticket)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
    
    return redirect(url_for('dashboard'))

@app.route('/nearby_mechanics/<int:ticket_id>')
@login_required
def nearby_mechanics(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Check if user owns this ticket
    if ticket.user_id != current_user.id:
        return redirect(url_for('dashboard'))
    
    # Check if we have coordinates
    if not ticket.latitude or not ticket.longitude:
        return render_template('error.html', 
                             error="Location coordinates not available for this ticket.")
    
    # Find nearby mechanics
    maps_service = GoogleMapsService(app.config['GOOGLE_MAPS_API_KEY'])
    mechanics_result = maps_service.find_nearby_mechanics(
        ticket.latitude, 
        ticket.longitude,
        radius=8000  # 8km radius
    )
    
    if mechanics_result['success']:
        # Calculate distances for each mechanic
        for mechanic in mechanics_result['mechanics']:
            distance_result = maps_service.calculate_distance(
                ticket.latitude, ticket.longitude,
                mechanic['latitude'], mechanic['longitude']
            )
            if distance_result['success']:
                mechanic['distance'] = distance_result['distance']
                mechanic['duration'] = distance_result['duration']
    
    return render_template('nearby_mechanics.html', 
                         ticket=ticket, 
                         mechanics=mechanics_result.get('mechanics', []),
                         api_key=app.config['GOOGLE_MAPS_API_KEY'])

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)