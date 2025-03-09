import os
from app.hashing import generate_checksum
from app.models import FileRecord
from app import db, create_app

def generate_initial_checksums(directory):
    app = create_app()
    with app.app_context():
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                checksum = generate_checksum(file_path)
                if not FileRecord.query.filter_by(checksum=checksum).first():
                    new_file = FileRecord(
                        checksum=checksum,
                        file_name=file,
                        file_path=file_path,
                        file_size=os.path.getsize(file_path),
                        file_type=os.path.splitext(file)[1]
                    )
                    db.session.add(new_file)
                    db.session.commit()
                    print(f"Checksum generated and stored for: {file_path}")

if __name__ == "__main__":
    directory_to_scan = r"C:\Users\aakas\Downloads"
    generate_initial_checksums(directory_to_scan)