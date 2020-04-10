from crabber import db, Crab, Molt

db.drop_all()
db.create_all()

# Create users
jake = Crab.create_new(username="jake",
                       email="contactjakeledoux@gmail.com",
                       password="***REMOVED***",
                       display_name="Jake Ledoux",
                       verified=True,
                       bio="I made this site.")

test_user = Crab.create_new(username="jake",
                            email="jaik.exe@gmail.com",
                            password="***REMOVED***",
                            display_name="Test User",
                            bio="test user, please ignore")
