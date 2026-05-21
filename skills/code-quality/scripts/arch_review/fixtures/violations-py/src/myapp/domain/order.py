from myapp.db import session  # VIOLATION: domain imports infrastructure


class Order:
    def save(self):
        session.persist(self)
