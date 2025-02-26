import logging
from celery import shared_task
import requests
from datetime import date, timedelta, datetime
from .models import TicketReport
from django.conf import settings
from django.core.mail import EmailMessage
from io import BytesIO

logger = logging.getLogger(__name__)

@shared_task
def fetch_daily_sga_report():
    """
    Task to  fetch the daily SGA report at 9.00 AM
    """
    #Calculate date range (yesterday to today)
    today = date.today()
    hace_30_dias = today - timedelta(days=30)

    try:
        with requests.Session() as session:
            response = session.post(
                settings.FASTAPI_URL,
                json={
                    "fecha_incio": hace_30_dias.isoformat(),
                    "fecha_fin": today.isoformat()
                },
                stream=True,
                timeout=1800 # Longer timeout for potentially large files 30 min (1 mes , lo que demora el sga)
            )
            response.raise_for_status()

            # Save content to ByteIO to avoid disk I/O
            excel_content = BytesIO()
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    excel_content.write(chunk)

            #Reset stream posiiton
            excel_content.seek(0)

            #Generate filename
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            report_filename= f"sga_report_{hace_30_dias}_to_{today}.xlsx"
            
            #prepare email
            subject = f"SGA Daily Report - {today}"
            message =f"""
            Hello,
            
            Attached is the SGA report for {hace_30_dias} to {today}.
            This is a automated email sent at {datetime.now()}.

            Regards,
            SGA Report System
            """

            # Create email
            email = EmailMessage(
                subject=subject,
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[settings.REPORT_EMAIL_RECIPIENT],   
            )

            # Attch excel file
            email.attach(report_filename, excel_content.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        
            #send email

            email.send(fail_silently=False)

            logger.info(f"Succesfully sent to SGA report email for {hace_30_dias}_to_{today}")
            return f"Email sent successfully to {settings.REPORT_EMAIL_RECIPIENT}"

    except requests.RequestException as e:
        logger.error(f"Failed to fech SGA report from FastAPI: {str(e)}")
        return f"Failed to fetch report: {str(e)}"
    except Exception as e:
        logger.exception(f"Unexpected error sending SGA report email: {str(e)}")
        return f"Error: {str(e)}"
