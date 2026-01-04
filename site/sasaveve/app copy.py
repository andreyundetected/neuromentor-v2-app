from flask_sqlalchemy import SQLAlchemy


app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db = SQLAlchemy(app)
