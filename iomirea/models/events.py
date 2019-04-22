"""
IOMirea-server - A server for IOMirea messenger
Copyright (C) 2019  Eugene Ershov

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from __future__ import annotations

import enum

from typing import Any, Dict


class EventScope(enum.Enum):
    LOCAL = 0
    OUTER = 1
    GLOBAL = 2


class Event:
    name = "BASE_EVENT"
    scope = EventScope.LOCAL

    def __init__(
        self,
        *,
        user_id: int = None,
        channel_id: int = None,
        payload: Dict[str, Any] = {},
    ):
        self.user_id = user_id
        self.channel_id = channel_id

        self._payload = payload

    @classmethod
    def from_data(cls, **data: Any) -> Event:
        event = cls(payload=data)
        event.parse_payload()

        return event

    def parse_payload(self) -> None:
        raise NotImplementedError

    @property
    def payload(self) -> Dict[str, Any]:
        return self._payload

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} user_id={self.user_id} channel_id={self.channel_id}>"


class MessageCreate(Event):
    name = "MESSAGE_CREATE"

    def parse_payload(self) -> None:
        self.user_id = self._payload["author"]["id"]
        self.channel_id = self._payload["channel_id"]
