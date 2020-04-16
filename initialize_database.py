from crabber import db, Crab, Molt

db.drop_all()
db.create_all()

# Create users
jake = Crab.create_new(username="jake",
                       email="contactjakeledoux@gmail.com",
                       password="fish",
                       display_name="Jake Ledoux",
                       verified=True,
                       bio="I made this site.")

crabber = Crab.create_new(username="crabber",
                          email="crabberwebsite@gmail.com",
                          password="fish",
                          display_name="Crabber",
                          verified=True,
                          bio="Official account for website news and updates.")

test_account = Crab.create_new(username="test_account",
                               email="jaik.exe@gmail.com",
                               password="fish",
                               display_name="Test Account",
                               verified=False,
                               bio="just testing around")
