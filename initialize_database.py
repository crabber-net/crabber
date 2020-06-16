from crabber import db, Crab, Molt, Trophy

db.drop_all()
db.create_all()

# Create crabber account
crabber = Crab.create_new(username="crabber",
                          email="crabberwebsite@gmail.com",
                          password="fish",
                          display_name="Crabber",
                          verified=True,
                          bio="Official account for website news and updates.")

# Initialize trophies
trophies = [
    Trophy(title="Social Newbie",
           description="Get your first follower"),
    Trophy(title="Mingler",
           description="Have 10 followers"),
    Trophy(title="Life of the Party",
           description="Have 100 followers"),
    Trophy(title="Celebrity",
           description="Have 1000 followers"),
    Trophy(title="Baby Crab",
           description="Publish your first Molt"),
    Trophy(title="Pineapple Express",
           description="Use the crabtag %420"),
    Trophy(title="I Want it That Way",
           description="Change your avatar, banner, and description"),
    Trophy(title="Dopamine Hit",
           description="Get 10 likes on a Molt"),
    Trophy(title="Dopamine Addict",
           description="Get 100 likes on a Molt. Need... more..."),
    Trophy(title="Full on Junkie",
           description="Get 1,000 likes on a Molt"),
    Trophy(title="Back-Crabber",
           description="Follow someone back only to have them unfollow you"),
    Trophy(title="I Captivated the Guy",
           description="Be followed by a verified user"),
    Trophy(title="Lab Rat",
           description="Participate in Crabber's beta phase"),
    Trophy(title="They Live",
           description="Survive the great site reset of 2020"),
]
for trophy in trophies:
    db.session.add(trophy)

db.session.commit()
