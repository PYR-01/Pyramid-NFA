import base64
import os

# Create your views here.
import requests
from PyPDF2 import PdfReader, PdfWriter
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.views import View
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def call_access_api():
    url = (
        "https://aplicarindia.my.salesforce.com/services/oauth2/token?grant_type=refresh_token&refresh_token"
        "=5Aep86158r93z6KIL4GeBBP6TAo9pGWdJoOgwyS3ufFXeCm1DIu.0dW2oj9Bjn1BV0UPd_Y60ISmjAoqj8hN3o_&client_id"
        "=3MVG9kb26yEQGZW3Ro6nN9tzMuOFdODD51ozQguu3ilw4VfzIXRkLwU44z2fQ7yQlBfBuu0tu_5vz85m3CMdp&client_secret"
        "=0B41C136365DC581086E6B6EEC607D46E74122C2D7FF7D80258F2E82A70338EC"
    )
    response = requests.post(url)
    if response.status_code == 200:
        token = response.json()["access_token"]
        return token


class Sign_View(View):

    def get(self, request, id):
        token = call_access_api()
        url = "https://aplicarindia.my.salesforce.com/services/apexrest/NFA_Doc_Api"

        payload = {"recordId": id}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

        response = requests.request("POST", url, headers=headers, json=payload)
        base64_pdf = response.json()["Files"][0]["Base64Data"]
        Title = response.json()["Files"][0]["Title"]
        Completed = response.json()["NFA"]
        context = {
            "base64_pdf": base64_pdf,
            "id": id,
            "Title": Title,
            "Completed": Completed,
        }
        return render(request, "sign.html", context)

    def post(self, request, id):
        data = request.POST.get("image")
        base64_string = request.POST.get("base64")
        remarks = request.POST.get("remarks")
        filename = request.POST.get("filename")
        approved = request.POST.get("approved")
        page_width, page_height = letter
        image_width = 398
        image_height = 198
        pdf_data = base64.b64decode(base64_string)

        # Write the binary data to a PDF file
        file_path = os.path.join(settings.MEDIA_ROOT, f"{filename}.pdf")
        with open(file_path, "wb") as pdf_file:
            pdf_file.write(pdf_data)
        if data:
            try:
                # Decode the base64 image and save it as a temporary PNG file
                format, imgstr = data.split(";base64,")
                img_data = base64.b64decode(imgstr)
                image_path = os.path.join(settings.MEDIA_ROOT, f"signature.png")
                with open(image_path, "wb") as f:
                    f.write(img_data)

                # Download the PDF from the provided URL and save it as a local file

                pdf_path = os.path.join(settings.MEDIA_ROOT, f"{filename}.pdf")

                # Read the existing PDF
                pdf_reader = PdfReader(pdf_path)
                pdf_writer = PdfWriter()

                # Create a watermark/signature PDF using the saved PNG image
                watermark_path = os.path.join(settings.MEDIA_ROOT, "watermark.pdf")
                c = canvas.Canvas(watermark_path, pagesize=letter)
                x = page_width - image_width
                y = 0  # Since you want it to be at the bottom, y is 0
                c.drawImage(
                    image_path, x, y, width=100, height=100, mask="auto"
                )  # Adjust position and size as needed
                c.save()

                # Merge the watermark onto the original PDF
                watermark_reader = PdfReader(watermark_path)

                for page_number in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_number]
                    page.merge_page(watermark_reader.pages[0])
                    pdf_writer.add_page(page)

                # Save the signed PDF to a file

                signed_pdf_path = os.path.join(
                    settings.MEDIA_ROOT,
                    f"Director_approved_{filename}.pdf",
                )
                with open(signed_pdf_path, "wb") as f:
                    pdf_writer.write(f)
                with open(signed_pdf_path, "rb") as pdf_file:
                    # Read the file's content
                    pdf_content = pdf_file.read()

                    # Encode the content as Base64
                base64_encoded_pdf = base64.b64encode(pdf_content)

                # Convert the Base64 bytes to a string
                base64_pdf_str = base64_encoded_pdf.decode("utf-8")
                token = call_access_api()
                url = "https://aplicarindia.my.salesforce.com/services/apexrest/NFA_DocSigned_Api"

                payload = {
                    "recordId": id,
                    "fileName": f"Director_approved_{filename}.pdf",
                    "base64FileContent": base64_pdf_str,
                    "isCompleted": approved,
                    "reason": remarks,
                }
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                }

                response = requests.request("POST", url, headers=headers, json=payload)
                print(response.json())
                # Return the signed PDF as a downloadable response

                os.remove(signed_pdf_path)
                os.remove(image_path)
                os.remove(watermark_path)
                os.remove(file_path)
                return HttpResponse("success", status=200)

            except:
                print("error")

        return HttpResponse(
            "Error: No signature image or PDF URL received.", status=400
        )


class NFA_Rejection(View):
    def post(self, request, id):
        remarks = request.POST.get("remarks2")
        approved = request.POST.get("approved")
        token = call_access_api()
        url = (
            "https://aplicarindia.my.salesforce.com/services/apexrest/NFA_DocSigned_Api"
        )

        payload = {
            "recordId": id,
            "fileName": f"",
            "base64FileContent": "",
            "isCompleted": approved,
            "reason": remarks,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

        response = requests.request("POST", url, headers=headers, json=payload)
        if response.json()["Status"] == "Success":
            return HttpResponse("Success", status=200)
        else:
            return HttpResponse("Error", status=400)
