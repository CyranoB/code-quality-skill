from myapp.domain import user as user_domain


def load(user_id):
    return user_domain.User(id=user_id)
