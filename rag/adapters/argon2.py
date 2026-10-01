import asyncio

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


class Argon2PasswordHasher:
    def __init__(self):
        self._hasher = PasswordHasher()

    async def hash(self, password: str) -> str:
        return await asyncio.to_thread(
            self._hasher.hash,
            password,
        )

    async def verify(
        self,
        hashed_password: str,
        password: str,
    ) -> bool:
        try:
            await asyncio.to_thread(
                self._hasher.verify,
                hashed_password,
                password,
            )
            return True
        except VerifyMismatchError:
            return False
