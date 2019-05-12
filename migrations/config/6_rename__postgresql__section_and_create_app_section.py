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
        app_section = {}
        app_section["port"] = self.config.pop("app-port")
        app_section["host"] = "0.0.0.0"
        self.config["app"] = app_section

        self.config["postgres"] = self.config.pop("postgresql")
