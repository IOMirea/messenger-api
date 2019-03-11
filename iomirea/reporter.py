import smtplib

import aiohttp


# TODO: different way of reporting errors


def send_report(text: str, app: aiohttp.web.Application) -> None:
    print(text)  # until a new way is found
    return

    text = f"Subject: IOMirea server error report\n\n{text}"
    config = app["config"]["error-reporter"]

    with smtplib.SMTP_SSL(config["smtp"]["host"]) as smtp:
        smtp.login(config["smtp"]["login"], config["smtp"]["password"])
        smtp.sendmail(
            config["smtp"]["login"], config["targets"], text.encode("utf8")
        )
