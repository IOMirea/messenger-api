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

import argparse


argparser = argparse.ArgumentParser(description="IOMirea server")

argparser.add_argument(
    "-d", "--debug", action="store_true", help="run server in debug mode"
)

argparser.add_argument(
    "--force-ssl",
    action="store_true",
    help="run https server (certificates paths should be configured)",
)

argparser.add_argument(
    "-e",
    "--with-eval",
    action="store_true",
    help="enable python eval endpoint (works only in debug mode)",
)

argparser.add_argument(
    "-s",
    "--with-static",
    action="store_true",
    help="enable static files support by server (works only in debug mode)",
)


args = argparser.parse_args()