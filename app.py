import os
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template, request
import requests
from supabase import Client, create_client

app = Flask(__name__)

# ตั้งค่า Supabase (เปลี่ยนเป็นค่าของคุณ หรือใช้ Environment Variable)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "YOUR_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "YOUR_SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


@app.route("/")
def index():
  # ดึงข้อมูลโรงเรียนทั้งหมดจาก Supabase มาแสดงที่หน้าเว็บ
  try:
    response = supabase.table("schools_admission").select("*").execute()
    schools = response.data
  except Exception as e:
    schools = []
    print(f"Error fetching data: {e}")

  return render_template("index.html", schools=schools)


@app.route("/run-scraper", methods=["POST"])
def run_scraper():
  """ฟังก์ชันรัน Scraper เพื่อดึงข้อมูลจากเว็บโรงเรียนมาอัปเดตลง Supabase"""
  try:
    response = supabase.table("schools_admission").select("*").execute()
    schools = response.data

    updated_count = 0
    for school in schools:
      school_id = school.get("id")
      school_name = school.get("school_name")
      url = school.get("website_link")

      if not url or url == "#":
        continue

      headers = {
          "User-Agent": (
              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
              " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
          )
      }
      res = requests.get(url, headers=headers, timeout=5)
      res.encoding = res.apparent_encoding

      if res.status_code == 200:
        soup = BeautifulSoup(res.text, "html.parser")
        page_text = soup.get_text()

        if "รับสมัคร" in page_text or "ม.1" in page_text:
          meta_desc = soup.find("meta", attrs={"name": "description"})
          extracted_text = (
              meta_desc["content"]
              if meta_desc and meta_desc.get("content")
              else "พบประกาศรับสมัครบนเว็บไซต์หลัก"
          )

          supabase.table("schools_admission").update({
              "deadline": f"อัปเดตจากเว็บ: {extracted_text[:80]}..."
          }).eq("id", school_id).execute()
          updated_count += 1

    return jsonify({
        "status": "success",
        "message": f"อัปเดตข้อมูลสำเร็จ {updated_count} โรงเรียน",
    })
  except Exception as e:
    return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
  app.run(debug=True, port=5000)