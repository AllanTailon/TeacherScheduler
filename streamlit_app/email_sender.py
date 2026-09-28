"""SMTP email distribution of per-teacher filtered rota attachments."""

from __future__ import annotations

import io
import re
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas as pd

from config import get_email_address, get_email_password
from export_ooxml import export_rota_for_teacher
from rota_io import load_rota_excel


def enviar_email_para_todos(combined_df, arquivo_rota) -> list[str]:
    log_messages: list[str] = []
    failed_teachers: list[str] = []

    if hasattr(arquivo_rota, "getvalue"):
        template_bytes = arquivo_rota.getvalue()
    elif isinstance(arquivo_rota, (bytes, bytearray)):
        template_bytes = bytes(arquivo_rota)
    else:
        with open(arquivo_rota, "rb") as file:
            template_bytes = file.read()

    _, _, sheet_name = load_rota_excel(io.BytesIO(template_bytes))

    from_email = get_email_address()
    password = get_email_password()

    server = None
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(from_email, password)

        for teacher in combined_df["Teacher"].unique():
            professor_data = combined_df[combined_df["Teacher"] == teacher]

            if professor_data.empty or pd.isna(teacher) or str(teacher).strip() == "":
                continue

            if "Email" not in professor_data.columns or pd.isna(professor_data["Email"].values[0]):
                log_messages.append(f"❌ No email found for {teacher}")
                failed_teachers.append(str(teacher))
                continue

            nome_grupo = professor_data["Nome Grupo"].dropna().astype(str).tolist()
            email_professor = professor_data["Email"].values[0]
            filtered_xlsx = export_rota_for_teacher(template_bytes, nome_grupo, sheet_name)

            nome_grupo_formatado = "\n".join(f"    {grupo}" for grupo in nome_grupo)
            message = (
                f"Hello {teacher},\n\n"
                f"You have been assigned to the following classes:\n\n"
                f"{nome_grupo_formatado}\n\n"
                f"Please find attached your detailed class schedule.\n\n"
                f"Best regards,\n"
                f"The Family Idiomas"
            )

            msg = MIMEMultipart()
            msg["From"] = from_email
            msg["To"] = email_professor
            msg["Subject"] = "Your Class Schedule"
            msg.attach(MIMEText(message, "plain"))

            safe_name = re.sub(r'[<>:"/\\|?*]+', "_", str(teacher).strip())
            part = MIMEBase("application", "octet-stream")
            part.set_payload(filtered_xlsx)
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{safe_name}_schedule.xlsx"',
            )
            msg.attach(part)

            try:
                server.sendmail(from_email, email_professor, msg.as_string())
                log_messages.append(f"✅ Email sent successfully to {teacher}")
            except Exception as exc:  # noqa: BLE001 — log per-teacher failures
                log_messages.append(f"❌ Failed to send email to {teacher}: {exc}")
                failed_teachers.append(str(teacher))
    finally:
        if server is not None:
            try:
                server.quit()
            except Exception:
                pass

    return log_messages
