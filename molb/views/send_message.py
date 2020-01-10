import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from aiohttp_jinja2 import get_env
from aiosmtplib import SMTP

from molb.views.auth.token import generate_token


async def send_text_message(request, to, subject, message):
    config = request.app["config"]

    message = MIMEText()
    message["subject"] = "[{}] {}".format(config["application"]["site_name"], subject)
    message["to"] = to
    message["from"] = config["application"]["from"]
    await request.app["mailer"].send_urgent_message(message)


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
    await request.app["mailer"].send_urgent_message(message)


class PriorityWrapper:
    def __init__(self, priority, obj):
        self.obj = obj
        self.priority = priority

    def __lt__(self, other):
        return self.priority < other.priority

    def __repr__(self):
        return "<PriorityWrapper priority={}, obj={}>".format(self.priority, repr(self.obj))


class SmtpMailer:
    def __init__(self, queue, delay, loop):
        self.loop = loop
        self.delay = delay
        self.queue = queue

        self.smtp = SMTP(hostname="127.0.0.1", port=25)

        self.timer = None
        self.task = asyncio.ensure_future(self.process_queue())

    async def connect(self):
        await self.smtp.connect()

    def deconnect(self):
        self.smtp.close()
        self.timer = None

    async def smtp_send(self, msg):
        await self.smtp.send_message(msg)

    async def process_queue(self):
        while True:
            item = await self.queue.get()

            if self.timer:
                self.timer.cancel()
                self.timer = self.loop.call_later(self.delay, self.deconnect)
            else:
                self.timer = self.loop.call_later(self.delay, self.deconnect)
                await self.connect()

            await self.smtp_send(item.obj)

    def close(self):
        if self.timer is not None:
            self.timer.cancel()
        self.task.cancel()


class MassMailer:
    def __init__(self, nbr_tasks=5, delay=30, loop=None):
        loop = loop if loop is not None else asyncio.get_event_loop()

        self.queue = asyncio.PriorityQueue(maxsize=4096)

        self.mailers = []
        for _ in range(nbr_tasks):
            self.mailers.append(SmtpMailer(self.queue, delay, loop))

    async def send_urgent_message(self, msg):
        await self.queue.put(PriorityWrapper(0, msg))

    async def send_message(self, msg):
        await self.queue.put(PriorityWrapper(1, msg))

    def close(self):
        for mailer in self.mailers:
            mailer.close()
