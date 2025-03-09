from app import db

class FileRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    checksum = db.Column(db.String(64), unique=True, nullable=False)
    file_name = db.Column(db.String(256), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False)  # Ensure this is BigInteger for large files
    file_type = db.Column(db.String(20), nullable=False)  # Increase length to 20
    date_created = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())