from crabber import db, Crab, Molt

db.drop_all()
db.create_all()

# pwd = Crab.hash_pass("fish")
pwd = "fish"

# User test
jake = Crab.create_new(username="jake",
                       email="contactjakeledoux@gmail.com",
                       password=pwd,
                       display_name="Jake Ledoux")

mezrah = Crab.create_new(username="mezinator5000",
                         email="mnavehm@gmail.com",
                         password=pwd,
                         display_name="Mezrah")

christian = Crab.create_new(username="DiFrankSinatra",
                            email="cdnation19@gmail.com",
                            password=pwd,
                            display_name="Christian 😊")

assert jake.register_time is not None
assert jake.verify_password("fish")
assert not jake.verify_password("anything else")

# Molt test
uno = jake.molt("What's the deal with airline ✈ food, anyway?")

assert uno.author == jake
assert uno in jake.molts
assert uno.timestamp is not None
assert len(uno.tags) == 0

# Molt test 2
dos = mezrah.molt("This site is %dumb. @jake, this is dumb.", image="https://i.imgur.com/GARoTYJ.jpg")

assert dos.author == mezrah
assert dos in mezrah.molts
assert dos.timestamp is not None
assert len(dos.tags) == 1
assert dos.tags[0] == "%dumb"
assert len(dos.mentions) == 1
assert dos.mentions[0] == jake

# Like test
alpha = dos.like(christian)
assert alpha in dos.likes
assert alpha in christian.likes
assert christian.likes[0].molt == dos
assert dos.like(christian) is None  # Liking something twice should not do anything
assert len(dos.likes) == 1
dos.unlike(christian)
assert len(dos.likes) == 0
dos.unlike(jake)  # Un-liking something that hasn't been liked should just ignore rather than throw an error

# Remolt test
tres = dos.remolt(christian)
assert tres.is_remolt
assert tres in dos.remolts
assert tres.original_molt == dos

# Follow test
for i in range(3):
    # 3 times to make sure you can't follow more than once
    jake.follow(mezrah)
    assert len(mezrah.followers) == 1 and jake in mezrah.followers
    assert len(jake.following) == 1 and mezrah in jake.following

jake.unfollow(mezrah)
assert len(mezrah.followers) == 0
assert len(jake.following) == 0

str(jake)
str(mezrah)
str(christian)

print("Test completed successfully.")
