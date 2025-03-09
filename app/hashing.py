import hashlib
import os
import time

def select_hashing_algorithm(file_size):
    if file_size < 1024 * 1024:  # Less than 1MB
        return 'md5'
    elif file_size < 10 * 1024 * 1024:  # Less than 10MB
        return 'sha1'
    else:
        return 'sha256'
    
def generate_checksum(file_path):
    retries = 3
    for attempt in range(retries):
        try:
            file_size = os.path.getsize(file_path)
            algorithm = select_hashing_algorithm(file_size)
            hash_func = getattr(hashlib, algorithm)()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_func.update(chunk)
            # Return the checksum if successful
            return hash_func.hexdigest()
        except PermissionError as e:
            print(f"Attempt {attempt + 1}: PermissionError: {e}")
            time.sleep(1)  # Wait before retrying
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
    # Return None if all attempts fail
    return None