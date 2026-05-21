from myapp.domain import user as user_domain


def fetch(user_id):
    return user_domain.User(id=user_id)
