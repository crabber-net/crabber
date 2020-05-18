from crabber import db, Crab, Molt

db.drop_all()
db.create_all()

# Create crabber account
crabber = Crab.create_new(username="crabber",
                          email="crabberwebsite@gmail.com",
                          password="fish",
                          display_name="Crabber",
                          verified=True,
                          bio="Official account for website news and updates.")
