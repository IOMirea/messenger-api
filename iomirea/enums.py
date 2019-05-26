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

import enum


class MessageTypes(enum.Enum):
    TEXT = 0
    CHANNEL_CREATE = 1
    CHANNEL_NAME_UPDATE = 2
    CHANNEL_ICON_UPDATE = 3
    CHANNEL_PIN_ADD = 4
    CHANNEL_PIN_REMOVE = 5
    RECIPIENT_ADD = 6
    RECIPIENT_REMOVE = 7


class Permissions(enum.Enum):
    MODIFY_CHANNEL = 1
    INVITE_MEMBERS = 2
    KICK_MEMBERS = 4
    BAN_MEMBERS = 8
    MODIFY_MEMBERS = 16
    DELETE_MESSAGES = 32
