import datetime
import threading

from flask import Flask, jsonify, request
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from marshmallow import Schema, fields, ValidationError, pre_load
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:////tmp/spots.db'
db = SQLAlchemy(app)

##### MODELS #####

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    email = db.Column(db.String(80))
    hashed_password = db.Column(db.String(80))
    vehicle_plate = db.Column(db.String(7))

class Spot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    is_reserved = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User",
                        backref=db.backref("spots"))
    reserved_at = db.Column(db.DateTime)
    reserved_due_to = db.Column(db.DateTime)
    hours_reserved = db.Column(db.Integer)
    is_occupied = db.Column(db.Integer)
    is_checked_in = db.Column(db.Integer)


##### SCHEMAS ##### 

class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str()
    email = fields.Str()
    hashed_password = fields.Str()
    vehicle_plate = fields.Str()


class SpotSchema(Schema):
    id = fields.Int(dump_only=True)
    is_reserved = fields.Int()
    user = fields.Nested(UserSchema, validate=must_not_be_blank)
    reserved_at = fields.DateTime()
    reserved_due_to = fields.DateTime()
    hours_reserved = fields.Int()
    is_occupied = fields.Int()
    is_checked_in = fields.Int()


user_schema = UserSchema()
users_schema = UserSchema(many=True)
spot_schema = SpotSchema()
spots_schema = SpotSchema(many=True)


###############################################################################################
############################################  API  ############################################
###############################################################################################


#THIS METHOD GETS ALL USERS 
@app.route('/users/', methods=['GET'])
def get_users():
    users = User.query.all()
    # Serialize the queryset
    result = users_schema.dump(users)
    return jsonify({'users': result.data}), 200


#THIS METHOD GETS ONE SPECIFIC USER
@app.route("/user/<int:pk>", methods=['GET'])
def get_user(pk):
    try:
        user = User.query.get(pk)
    except IntegrityError:
        # Informs the user ERROR 400 - Bad Request
        return jsonify({"message": "User could not be found on Database."}), 400
    user_result = user_schema.dump(user)
    spots_result = spots_schema.dump(user.spots.all())
    return jsonify({'user': user_result.data, 'spots': spots_result.data}), 200


#THIS METHOD ALLOW USERS TO LOGIN INTO THE SYSTEM 
@app.route("/user/login/", methods=["POST"])
def validateUser():
    json_data = request.get_json()
    if not json_data:
        return jsonify({'message': 'No input data provided'}), 400
    data, errors = user_schema.load(json_data)
    if errors:
        return jsonify(errors), 422
    email = json_data['email']
    plain_password = json_data['password']      
    user = User.query.filter_by(email=email).first()
    if user is None:
        return jsonify({'message': 'User does not exists!'}), 404
    else:
        if check_password_hash(user.hashed_password, plain_password):
            result = user_schema.dump(user)
            print('INICIO DO RESULT DATA')
            print(result.data)
            print('FIM DO RESULT DATA')
            return jsonify({"user": result.data}), 200
        else:       
            return jsonify({'message':'Wrong password! , Please try again.'}), 401


#THIS METHOD CREATES A NEW USER BY REGISTRATION 
@app.route("/user/", methods=["POST"])
def create_user():
    json_data = request.get_json()
    if not json_data:
        # Informs the user ERROR 400 - Bad Request
        return jsonify({'message': 'No input data provided'}), 400
    # Validate and deserialize input
    data, errors = user_schema.load(json_data)
    if errors:
        return jsonify(errors), 422    
    name = json_data['name']    
    email = json_data['email']
    plain_password = json_data['password']
    hashedPassword = generate_password_hash(plain_password)
    vehicle_plate = json_data['vehicle_plate']
    user = User.query.filter_by(email=email).first()
    if user is None:
        # Create a new user
        user = User(name = name, email = email, hashed_password = hashedPassword, vehicle_plate = vehicle_plate)
        db.session.add(user)
    else:
        #Informs the user ERROR 409 - Conflict  
        return jsonify({'message': 'User already exists!'}),409 
            
    db.session.commit()
    result = user_schema.dump(User.query.get(user.id))
    return jsonify({"message": "Created new User.",
                    "user": result.data}), 200


#---------------------------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------------------

#THIS METHOD GETS ALL SPOTS
@app.route('/spots/', methods=['GET'])
def get_spots():
    #get all spot objects
    spots = Spot.query.all()
    #using that spot objects, we dump the data associated with each of them from the database
    result = spots_schema.dump(spots)
    print('INICIO DO RESULT DATA GET SPOTS')
    print(result.data)
    print('FIM DO RESULT DATA GET SPOTS')
    return jsonify({"spots": result.data}), 200


#THIS METHOD GETS A SPECIFIC SPOT
@app.route("/spot/<int:pk>", methods=['GET'])
def get_spot(pk):
    try:
        spot = Spot.query.get(pk)
    except IntegrityError:
        return jsonify({"message": "Spot could not be found on Database."}), 400
    result = spot_schema.dump(spot)
    return jsonify({"spot": result.data}), 200



#THIS METHOD UPDATES THE SPOT TO ASSIGN IT TO A NEW OWNER 
@app.route("/spot/update/", methods=["POST"])
def update_spot():
    json_data = request.get_json()
    print('INICIO DO JSON')
    print(json_data)
    print('FIM DO JSON')
    if not json_data:
        return jsonify({'message': 'No input data provided'}), 400
    # Validate and deserialize input
    data, errors = spot_schema.load(json_data)
    if errors:
        return jsonify(errors), 422
    print('INICIO DO DATA')    
    print(data) 
    print('FIM DO DATA')
       
    spotID = json_data['id']
    spotHoursToReserve = json_data['hours_reserved']
    spot = Spot.query.get(spotID)

    print('Spot ID:')
    print(spot.id)
    print('------------')
    print('Old owner ID:')
    print(spot.user.id)
    print('Old owner EMAIL:')
    print(spot.user.email)
  

    userEmail = json_data['user']['email']
    newOwner = User.query.filter_by(email=userEmail).first()

    print('New owner ID:')
    print(newOwner.id)
    print('New owner EMAIL:')
    print(newOwner.email)

    
    newReserveTime = datetime.datetime.now()
    oldReserveTime = spot.reserved_due_to

    print('NEW TIME:')
    print(newReserveTime)
    print('OLD TIME:')
    print(oldReserveTime)

    if (newReserveTime < oldReserveTime) or (spot.is_occupied == 1):
        return jsonify({"message": "Forbidden reserve. The spot is still reserved or occupied."}),403
    else:    
        #UPDATE THE SELECTED "SPOT" WITH THE NEW OWNER OBJECT
        spot.user_id = newOwner.id
        spot.is_reserved = 1
        spot.hours_reserved = spotHoursToReserve
        spot.reserved_at = datetime.datetime.now()
        spot.reserved_due_to = datetime.datetime.now() + datetime.timedelta(hours = spotHoursToReserve)
    
        db.session.add(spot)
        db.session.commit()
        return jsonify({"message": "Updated spot successfully."}), 200

            

#THIS METHOD CHECK IN THE SPOT ASSIGNED TO A USER 
@app.route("/spot/checkIn/", methods=["POST"])
def check_in_spot():
    json_data = request.get_json()
    print('INICIO DO JSON')
    print(json_data)
    print('FIM DO JSON')
    if not json_data:
        return jsonify({'message': 'No input data provided'}), 400
    # Validate and deserialize input
    data, errors = spot_schema.load(json_data)
    if errors:
        return jsonify(errors), 422
    print('INICIO DO DATA')    
    print(data) 
    print('FIM DO DATA')
       
    spotID = json_data['id']
    spotHoursToReserve = json_data['hours_reserved']
    spot = Spot.query.get(spotID)

    print('Spot ID:')
    print(spot.id)
    print('------------')
    print('Old owner ID:')
    print(spot.user.id)
    print('Old owner EMAIL:')
    print(spot.user.email)
  

    userEmail = json_data['user']['email']
    newOwner = User.query.filter_by(email=userEmail).first()

    print('New owner ID:')
    print(newOwner.id)
    print('New owner EMAIL:')
    print(newOwner.email)

    
    newReserveTime = datetime.datetime.now()
    oldReserveTime = spot.reserved_due_to

    print('NEW TIME:')
    print(newReserveTime)
    print('OLD TIME:')
    print(oldReserveTime)

    if (spot.is_reserved == 1):
        #UPDATE THE SELECTED "SPOT" WITH THE NEW OWNER OBJECT
        spot.is_checked_in = 1
        db.session.add(spot)
        db.session.commit()
        return jsonify({"message": "Checked in spot successfully."}), 200
    else:
        return jsonify({"message": "NOT Checked in. The spot is still not reserved."}),403       



#THIS METHOD IS USED BY ADMIN TO CREATE AN EMPTY USER
@app.route("/spot/", methods=["POST"])
def create_spot():
    json_data = request.get_json()
    if not json_data:
        # Informs the user ERROR 400 - Bad Request
        return jsonify({'message': 'No input data provided'}), 400
    # Validate and deserialize input
    data, errors = spot_schema.load(json_data)
    if errors:
        return jsonify(errors), 422
    name = json_data['user']['name']    
    email = json_data['user']['email']
    plain_password = json_data['user']['password']
    hashedPassword = generate_password_hash(plain_password)
    vehicle_plate = json_data['user']['vehicle_plate']
    user = User.query.filter_by(email=email).first()
    if user is None:
        # Create a new user
        user = User(name = name, email = email, hashed_password = hashedPassword, vehicle_plate = vehicle_plate)
        db.session.add(user)
    # Create new spot
    spot = Spot(
        is_reserved = 0,
        user=user,
        reserved_at= datetime.datetime.now(),
        reserved_due_to = datetime.datetime.now() + datetime.timedelta(hours = 1),
        hours_reserved = 1,      # data['hours_reserved']
        is_occupied = 0,
        is_checked_in = 0
    )
    db.session.add(spot)
    db.session.commit()
    result = spot_schema.dump(Spot.query.get(spot.id))
    return jsonify({"message": "Created new Spot.",
                    "spot": result.data}), 200




#THIS METHOD IS USED BY ADMIN TO INITIALLY POPULATE THE PARKING LOT OR JUST TO CREATE AN EMPTY SPOT
@app.route("/spot/new_empty/", methods=["GET"])
def create_empty_spot():
    user = User.query.filter_by(email='empty@admin.com').first()
    if user is None:
        # Create a new user
        plain_password = '<admin>'
        hashedPassword = generate_password_hash(plain_password)
        user = User(name = '<empty>', email = 'empty@admin.com', hashed_password = hashedPassword, vehicle_plate = '<empty>')
        db.session.add(user)
    # Create new spot
    spot = Spot(
        is_reserved = 0,
        user=user,
        reserved_at= datetime.datetime.now(),
        reserved_due_to = datetime.datetime.now(),
        hours_reserved = 0,
        is_occupied = 0,
        is_checked_in = 0
    )
    db.session.add(spot)
    db.session.commit()
    result = spot_schema.dump(Spot.query.get(spot.id))
    return jsonify({"message": "Created an Empty Spot successfully.",
                    "spot": result.data}), 200


#THIS METHOD CREATES ADMIN USER AND FIRST SPOT
def create_admin():
    user = User.query.filter_by(email='empty@admin.com').first()
    if user is None:
        # Create a new user
        plain_password = '<admin>'
        hashedPassword = generate_password_hash(plain_password)
        user = User(name = '<empty>', email = 'empty@admin.com', hashed_password = hashedPassword, vehicle_plate = '<empty>')
        db.session.add(user)
    # Create new spot
    spot = Spot(
        is_reserved = 0,
        user=user,
        reserved_at= datetime.datetime.now(),
        reserved_due_to = datetime.datetime.now(),
        hours_reserved = 0,
        is_occupied = 0,
        is_checked_in = 0
    )
    db.session.add(spot)
    db.session.commit()



#THIS METHOD CLEANS UP ALL THE SPOTS, LOKING FOR EXTRAPOLATED TIME SPOTS, AND THEN REFRESH THEM TO NEW INCOME USERS USE AGAIN.
def clean_spots():
    threading.Timer(60, clean_spots).start()
    #get all spot objects
    spots = Spot.query.all()
    #Check all the spots that extrapolate the reservation time limit, to clean up them to new income users
    if spots is not None:
        for spot in spots:
            if spot.reserved_due_to < datetime.datetime.now():
                spot.user_id = 1
                spot.is_reserved = 0
                spot.reserved_at = datetime.datetime.now()
                spot.reserved_due_to = datetime.datetime.now()
                spot.hours_reserved = 0

                db.session.add(spot)
                db.session.commit()
        print('Extrapolated time spots are now released...')            




if __name__ == '__main__':
    db.create_all()
    create_admin()
    # CLEAN UP ALL OVERTIMED SPOTS
    clean_spots()
    app.run(debug=True, port=5000,host='0.0.0.0')