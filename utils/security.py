import bcrypt
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed_pass):
    return bcrypt.checkpw(password.encode('utf-8'), hashed_pass.encode('utf-8'))