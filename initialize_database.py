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

crabber = Crab.create_new(username="crabber",
                          email="jaik.exe@gmail.com",
                          password="***REMOVED***",
                          display_name="Crabber",
                          verified=True,
                          bio="Official account for website news and updates.")
