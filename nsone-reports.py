#!/usr/bin/env python3
from datetime import datetime, timedelta
from itertools import chain
from pathlib import Path
from sys import exit as sys_exit
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader, select_autoescape
from requests import Session as reqSession

import argparse
import configparser
import smtplib
import yaml
import logging


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--unit",
        default="hours",
        choices=[
            "days",
            "seconds",
            "microseconds",
            "milliseconds",
            "minutes",
            "hours",
            "weeks",
        ],
        help="set unit for timestamp calculation (default: %(default)s)",
    )
    parser.add_argument(
        "--amount",
        default=1,
        type=int,
        help="set number of units for timestamp calculation (default: %(default)s)",
    )
    parser.add_argument(
        "--limit",
        "-l",
        default=20,
        type=int,
        help="limit number of returned records (default: %(default)s)",
    )
    parser.add_argument(
        "--config", help="path to config file", default="~/.nsone_reports.ini"
    )
    parser_export = parser.add_argument_group()
    parser_export.add_argument(
        "--export",
        "-e",
        action="store_true",
        help="export report in same format as in NS1 gui",
    )
    parser_export.add_argument(
        "--format",
        default="json",
        choices=["json", "xml", "csv", "pdf", "xlsx", "html"],
        help="filetype of generated report (default: %(default)s)",
    )
    parser_mail = parser.add_argument_group()
    parser_mail.add_argument(
        "--mailfrom", default=None, type=str, help="sender address"
    )
    parser_mail.add_argument(
        "--mailto",
        default=None,
        type=str,
        help="recipient address separated by comma (default: %(default)s)",
    )
    parser.add_argument(
        "--silent", "-s", action="store_true", help="don't print report to stdout"
    )
    return parser.parse_args()


def parse_config(path):
    cfg = Path(path).expanduser()
    if cfg.exists():
        conf = configparser.ConfigParser()
        with open(cfg) as c:
            conf.read_file(c)
        return conf
    else:
        sys_exit(f"Config file {path} not found!")


def get_reports(api_key, unit="hours", amount=1, limit=20, export=None, fmt=None):
    with reqSession() as s:
        s.headers["X-NSONE-Key"] = api_key
        s.headers["charset"] = "utf-8"
        epoch = datetime(1970, 1, 1)
        td_args = {unit: amount}
        d = datetime.utcnow() - timedelta(**td_args)
        start_from = int((d - epoch).total_seconds())
        params = {
            "start": start_from,
            "limit": limit,
        }
        if export:
            params["export"] = fmt
        try:
            r = s.get("https://api.nsone.net/v1/account/activity", params=params)
        except Exception as e:
            logging.error(e)
            sys_exit(e)
    if r.status_code == 200:
        return r.content if export else r.json()
    else:
        logging.error(f"r.json() = {r.json()}")
        return r.json().get("message")


def convert_timestamp(timestamp, fmt="%d.%m.%Y %H:%M:%S"):
    dt_object = datetime.fromtimestamp(int(timestamp))
    return dt_object.strftime(fmt)


def parse_reports(reports):
    output = []
    if len(reports) != -1:
        for item in reports:
            logging.debug(f"item = {item}")
            try:
                result = {}
                output.append("---\n")
                result["user_name"] = item.get("user_name")
                result["user_id"] = item.get("user_id")
                if item.get("zone"):
                    result["zone"] = item["resource"].get("zone")
                result["time"] = convert_timestamp(item.get("timestamp"))
                result["action"] = item.get("action")
                if item["resource"].get("type"):
                    result["type"] = item["resource"].get("type")
                if item["resource"].get("domain"):
                    result["domain"] = item["resource"].get("domain")
                if item["resource"].get("answers"):
                    result["answers"] = list(
                        chain.from_iterable(
                            [i["answer"] for i in item["resource"]["answers"]]
                        )
                    )
                else:
                    result["resource"] = item.get("resource")
                output.append(yaml.dump(result, sort_keys=False, allow_unicode=True))
                output.append("\n")
            except KeyError as e:
                logging.error(f"item = {item}")
                sys_exit(e)

    return "".join(output)


def send_mail(
    mailfrom, mailto, server, user, password, body, formatting=None, port=465
):
    toaddrs = mailto.split(",")
    message = MIMEMultipart("alternative")
    message["Subject"] = "NS1 Activity Report"
    message["From"] = mailfrom
    message["To"] = mailto
    # TODO attachment pdf xlsx
    message.attach(MIMEText(body, "plain", "utf-8"))
    if formatting == "html":
        html_part = MIMEText(body, "html", "utf-8")
        message.attach(html_part)
    else:
        plain_part = MIMEText(body, "plain", "utf-8")
        env = Environment(
            loader=FileSystemLoader(
                Path(__file__).resolve().parent.joinpath("templates")
            ),
            autoescape=select_autoescape(["html"]),
        )
        template = env.get_template("nsone-report.html.j2")
        html_part = MIMEText(
            template.render(body=body, title="NS1 Activity Report"), "html", "utf-8"
        )
        message.attach(plain_part)
        message.attach(html_part)
    server = smtplib.SMTP_SSL(server, port)
    if user and password:
        server.login(user, password)
    try:
        server.sendmail(mailfrom, toaddrs, message.as_string())
    except Exception as e:
        sys_exit(e)
    finally:
        server.quit()


if __name__ == "__main__":
    args = parse_args()
    config = parse_config(args.config)
    log_name = Path(__file__).name.replace(".py", ".log")
    log_dir = Path(config.get("nsone", "NSONE_LOGDIR")).expanduser()
    log_path = log_dir.joinpath(log_name)
    try:
        logging.basicConfig(
            format="%(time)s | %(levelname)-8s | %(message)s",
            filename=log_path,
            filemode="a",
            level=logging.DEBUG,
        )
    except FileNotFoundError as e:
        logging.error(f"Unable to open {log_path}")
        sys_exit(e)
    except PermissionError as e:
        logging.error(f"Permission denied for {log_path}")
        sys_exit(e)

    report_params = {
        "api_key": config.get("nsone", "NSONE_API_KEY"),
        "unit": args.unit,
        "amount": args.amount,
        "limit": args.limit,
        "export": args.export,
        "fmt": args.format,
    }
    logging.debug(f"report_params = {report_params}")
    report = get_reports(**report_params)
    logging.debug(f"report = {report}")
    parsed_reports = parse_reports(report) if not args.export else report

    # TODO save exports to file
    if not args.mailto or args.silent:
        print(parsed_reports if not args.export else parsed_reports.decode("utf-8"))

    if args.mailto and len(parsed_reports) != 0:
        mail_params = {
            "header": args.header
            if args.header
            else config.get("mail", "header", fallback=None),
            "footer": args.footer
            if args.footer
            else config.get("mail", "footer", fallback=None),
            "mailfrom": args.mailfrom
            if args.mailfrom
            else config.get("smtp", "from", fallback="localhost"),
            "mailto": args.mailto
            if args.mailto
            else config.get("smtp", "mailto", fallback=None),
            "server": config.get("smtp", "server", fallback="localhost"),
            "user": config.get("smtp", "username", fallback=None),
            "password": config.get("smtp", "password", fallback=None),
            "body": parsed_reports,
            "formatting": args.format if args.export else None,
            "port": config.getint("smtp", "port", fallback=465),
        }
        send_mail(**mail_params)
