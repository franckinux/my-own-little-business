from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from aiohttp_jinja2 import get_env
from aiosmtplib import SMTP

from views.auth.token import generate_token


class SmtpSendingError(Exception):
    pass


async def send_message(message, config):
    host = config["url"]
    port = int(config["port"])
    username = config["username"]
    password = config["password"]
    use_tls = False if port == 587 else True
    try:
        # https://stackoverflow.com/questions/10147455/
        # how-to-send-an-email-with-gmail-as-provider-using-python
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


async def send_confirmation(
    request, email_address, token_data, route, subject, template_name
):
    config = request.app["config"]

    token = generate_token(config["application"]["secret_key"], **token_data)
    url = config["application"]["url"] + \
        str(request.app.router[route].url_for(token=token))

    env = get_env(request.app)
    template = env.get_template("auth/{}.txt".format(template_name))
    text_part = template.render(url=url)
    text_message = MIMEText(text_part, "plain")
    template = env.get_template("auth/{}.html".format(template_name))
    html_part = template.render(url=url)
    html_message = MIMEText(html_part, "html")

    message = MIMEMultipart("alternative")
    message["subject"] = "[{}] {}".format(config["application"]["site_name"], subject)
    message["to"] = email_address
    message["from"] = config["application"]["from"]
    message.attach(text_message)
    message.attach(html_message)
    await send_message(message, config["smtp"])
