from aiosmtplib import SMTP


class SmtpSendingError(Exception):
    pass


async def send_message(message, config):
    host = config["smtp"]["url"]
    port = int(config["smtp"]["port"])
    username = config["smtp"]["ssername"]
    password = config["smtp"]["password"]
    use_tls = False if port == 587 else True
    try:
        # https://stackoverflow.com/questions/10147455/how-to-send-an-email-with-gmail-as-provider-using-python
        smtp = SMTP(hostname=host, port=port, use_tls=use_tls)
        await smtp.connect()
        if port == 587:
            await smtp.ehlo()
            await smtp.starttls()
            await smtp.login(username, password)
        await smtp.send_message(message)
        smtp.close()
    except:
        raise SmtpSendingError("error while exchanging with smtp server")
