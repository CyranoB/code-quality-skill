from myapp.services import user_service


def get_user(user_id: int):
    return user_service.fetch(user_id)
