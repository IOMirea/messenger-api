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


from migration import ConfigMigration


class Migration(ConfigMigration):
    async def up(self, latest: int) -> None:
        self.config["email-confirmation"] = {
            "smtp": {
                "host": "EMAIL-CONFIRMATION-SMTP-HOST",
                "login": "EMAIL-CONFIRMATION-SMTP-LOGIN",
                "password": "EMAIL-CONFIRMATION-SMTP-PASSWORD",
            }
        }

    async def down(self) -> None:
        self.config.pop("email-confirmation")
