from django.contrib.auth.models import User

existing_users = User.objects.filter(email='bryanbarrios89@gmail.com')
if existing_users.exists():
    for user in existing_users:
        print(user.username)
else:
    print("No existing user with this email.")
