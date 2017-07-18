from aiohttp_jinja2 import get_env
from aiosmtplib import SMTP
from email.message import Message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer


def get_id_from_token(token, secret_key):
    s = Serializer(secret_key)
    data = s.loads(token)
    return data["confirm"]


def generate_confirmation_token(id_, secret_key, expiration=3600):
    s = Serializer(secret_key, expiration)
    return s.dumps({"confirm": id_}).decode("ascii")


class SmtpSendingError(Exception):
    pass


async def send(message, config):
    host = config["smtp_url"]
    port = int(config["smtp_port"])
    username = config["smtp_username"]
    password = config["smtp_password"]
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


async def send_confirmation(app, client):
    config = app["config"]["application"]

    token = generate_confirmation_token(client.id, config["secret_key"])
    url = "{}/confirm/{}/".format(config["url"], token)

    env = get_env(app)
    template = env.get_template("auth/confirmation-message.txt")
    text_part = template.render(url=url)
    text_message = MIMEText(text_part, "plain")
    template = env.get_template("auth/confirmation-message.html")
    html_part = template.render(url=url)
    html_message = MIMEText(html_part, "html")

    message = MIMEMultipart("alternative")
    message["subject"] = "Confirm your account"
    message["to"] = client.email_address
    message["from"] = config["from"]
    message.attach(text_message)
    message.attach(html_message)
    await send(message, config)
