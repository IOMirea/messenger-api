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
        email_conf_section = self.config["email-confirmation"]["smtp"]
        if email_conf_section["host"] == "EMAIL-CONFIRMATION-SMTP-HOST":
            email_conf_section["host"] = None
        if email_conf_section["login"] == "EMAIL-CONFIRMATION-SMTP-LOGIN":
            email_conf_section["login"] = None
        if (
            email_conf_section["password"]
            == "EMAIL-CONFIRMATION-SMTP-PASSWORD"
        ):
            email_conf_section["password"] = None

        error_reporter_section = self.config["error-reporter"]["smtp"]
        if error_reporter_section["host"] in ("SMTP-HOST", "HOST"):
            error_reporter_section["host"] = None
        if error_reporter_section["login"] in ("SMTP-LOGIN", "LOGIN"):
            error_reporter_section["login"] = None
        if error_reporter_section["password"] in ("SMTP-PASSWORD", "PASSWORD"):
            error_reporter_section["password"] = None

        if self.config["error-reporter"]["targets"] == ["EMAIL"]:
            self.config["error-reporter"]["targets"] = []

        if self.config["github-webhook-token"] in ("", "TOKEN"):
            self.config["github-webhook-token"] = None

        postgres_section = self.config["postgresql"]
        if postgres_section["database"] == "POSTGRES-DATABASE":
            postgres_section["database"] = None
        if postgres_section["password"] == "POSTGRES-PASSWORD":
            postgres_section["password"] = None
        if postgres_section["user"] == "POSTGRES-USER":
            postgres_section["user"] = None

        if self.config["ssl"]["cert-chain-path"] == "CERT-CHAIN-PATH":
            self.config["ssl"]["cert-chain-path"] = None
        if self.config["ssl"]["cert-privkey-path"] == "CERT-PRIVKEY-PATH":
            self.config["ssl"]["cert-privkey-path"] = None
