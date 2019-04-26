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

from typing import Any, Dict


class Event:
    __slots__ = ("_payload",)

    def __init__(self, *, payload: Dict[str, Any]):
        self._payload = payload
        self._parse_payload()

    def _parse_payload(self) -> None:
        raise NotImplementedError

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @property
    def payload(self) -> Dict[str, Any]:
        return self._payload


class LocalEvent(Event):
    __slots__ = ("channel_id",)

    def __init__(self, **kwargs: Any):
        self.channel_id = -1

        super().__init__(**kwargs)

        if self.channel_id == -1:
            raise RuntimeError(
                "channel_id field of LocalEvent should not be None"
            )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} channel_id={self.channel_id}>"


class OuterEvent(Event):
    __slots__ = ("user_id",)

    def __init__(self, **kwargs: Any):
        self.user_id = -1

        super().__init__(**kwargs)

        if self.user_id == -1:
            raise RuntimeError(
                "user_id field of OuterEvent should not be None"
            )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} user_id={self.user_id}>"


class GlobalEvent(Event):
    pass


class MESSAGE_CREATE(LocalEvent):
    def parse_payload(self) -> None:
        self.channel_id = self._payload["channel_id"]


class CHANNEL_UPDATE(LocalEvent):
    def _parse_payload(self) -> None:
        self.channel_id = self._payload["id"]


class USER_UPDATE(OuterEvent):
    def _parse_payload(self) -> None:
        self.user_id = self._payload["id"]
