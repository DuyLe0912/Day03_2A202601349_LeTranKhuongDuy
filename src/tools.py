"""
🛠️ TOOL REGISTRY & SCHEMAS (Dành cho Role 2: Tool & Spec Engineer)
Đề tài: Trợ Lý Sàng Lọc Hồ Sơ Tuyển Dụng & Hẹn Phỏng Vấn
Nơi khai báo tất cả các "món đồ nghề" mà ReAct Agent có thể gọi.

Ghi chú: Dữ liệu (skill chuẩn của job, lịch rảnh interviewer...) được MÔ PHỎNG
bằng biến cứng (mock data) để phục vụ demo trong buổi Lab, chưa kết nối
CSDL/API thật.
"""

# ============================================================
# 🔧 MOCK DATA (dữ liệu giả lập dùng chung cho các tool)
# ============================================================

# Yêu cầu kỹ năng chuẩn cho từng vị trí tuyển dụng
JOB_REQUIREMENTS = {
    "data analyst": ["python", "sql", "excel", "power bi"],
    "backend developer": ["python", "django", "sql", "docker"],
    "ai engineer": ["python", "pytorch", "machine learning", "sql"],
}

# Lịch rảnh của từng interviewer theo ngày (giờ còn trống)
INTERVIEWER_SCHEDULE = {
    "anh minh": {"2026-08-01": ["09:00", "10:00", "14:00"]},
    "chị lan": {"2026-08-01": ["13:00", "15:00"], "2026-08-02": ["09:00"]},
}

# Nơi lưu tạm các lịch phỏng vấn đã đặt (mô phỏng database)
BOOKED_INTERVIEWS = []


# ============================================================
# 🧩 NHÓM 1: SÀNG LỌC HỒ SƠ (Resume Screening)
# ============================================================

def extract_resume_info(resume_text: str) -> dict:
    """
    Trích xuất thông tin có cấu trúc (họ tên, kỹ năng, số năm kinh nghiệm)
    từ nội dung thô của một CV.

    Args:
        resume_text (str): Toàn bộ nội dung văn bản của CV
                            (ví dụ: "Nguyen Van A. Ky nang: Python, SQL. 2 nam kinh nghiem.")

    Returns:
        dict: Thông tin đã trích xuất, gồm các khóa:
            - "ho_ten" (str): họ tên ứng viên (dòng đầu tiên của CV)
            - "ky_nang" (list[str]): danh sách kỹ năng tìm thấy trong CV
            - "so_nam_kinh_nghiem" (int): số năm kinh nghiệm (0 nếu không tìm thấy)
        Nếu resume_text rỗng, trả về dict với "loi" (str) mô tả lỗi.
    """
    if not resume_text or not isinstance(resume_text, str) or not resume_text.strip():
        return {"loi": "LỖI: Nội dung CV trống hoặc không đúng định dạng văn bản."}

    text_lower = resume_text.lower()
    ho_ten = resume_text.strip().split("\n")[0].split(".")[0].strip()

    # Danh sách kỹ năng tham chiếu để dò tìm trong văn bản CV
    known_skills = ["python", "sql", "excel", "power bi", "django",
                     "docker", "pytorch", "machine learning", "java", "c++"]
    ky_nang = [skill for skill in known_skills if skill in text_lower]

    # Dò số năm kinh nghiệm dạng "X năm"
    so_nam = 0
    import re
    match = re.search(r"(\d+)\s*n[ăa]m", text_lower)
    if match:
        so_nam = int(match.group(1))

    return {
        "ho_ten": ho_ten,
        "ky_nang": ky_nang,
        "so_nam_kinh_nghiem": so_nam,
    }


def match_resume_to_job(candidate_skills: list, job_title: str) -> dict:
    """
    So khớp danh sách kỹ năng của ứng viên với yêu cầu kỹ năng của một vị trí
    tuyển dụng, tính ra điểm phù hợp (%).

    Args:
        candidate_skills (list[str]): Danh sách kỹ năng của ứng viên
                                       (ví dụ: ["python", "sql"])
        job_title (str): Tên vị trí tuyển dụng, phải khớp (không phân biệt hoa
                          thường) với một khóa trong JOB_REQUIREMENTS
                          (ví dụ: "Data Analyst")

    Returns:
        dict: Kết quả so khớp, gồm các khóa:
            - "diem_phu_hop" (float): phần trăm kỹ năng khớp (0-100)
            - "ky_nang_khop" (list[str]): các kỹ năng ứng viên có và job cần
            - "ky_nang_thieu" (list[str]): các kỹ năng job cần nhưng ứng viên chưa có
        Nếu job_title không tồn tại trong JOB_REQUIREMENTS, trả về dict với
        "loi" (str) mô tả lỗi.
    """
    if not job_title or not isinstance(job_title, str):
        return {"loi": "LỖI: Thiếu tên vị trí tuyển dụng (job_title)."}

    job_key = job_title.lower().strip()
    if job_key not in JOB_REQUIREMENTS:
        return {"loi": f"LỖI: Không tìm thấy yêu cầu tuyển dụng cho vị trí '{job_title}'."}

    if not candidate_skills or not isinstance(candidate_skills, list):
        return {"loi": "LỖI: candidate_skills phải là một danh sách (list) kỹ năng, không được để trống."}

    required = set(JOB_REQUIREMENTS[job_key])
    candidate = set(str(s).lower() for s in candidate_skills)

    khop = sorted(required & candidate)
    thieu = sorted(required - candidate)
    diem = round(len(khop) / len(required) * 100, 1) if required else 0.0

    return {
        "diem_phu_hop": diem,
        "ky_nang_khop": khop,
        "ky_nang_thieu": thieu,
    }


def filter_candidates(candidates: list, min_score: float) -> list:
    """
    Lọc ra các ứng viên có điểm phù hợp đạt ngưỡng tối thiểu.

    Args:
        candidates (list[dict]): Danh sách ứng viên, mỗi phần tử là dict có
                                  khóa "ho_ten" (str) và "diem_phu_hop" (float)
                                  (ví dụ: [{"ho_ten": "A", "diem_phu_hop": 80.0}, ...])
        min_score (float): Ngưỡng điểm tối thiểu để được giữ lại (0-100)

    Returns:
        list[dict]: Danh sách ứng viên đạt ngưỡng, đã sắp xếp giảm dần theo
                     "diem_phu_hop". Trả về danh sách rỗng nếu không có ai đạt.
    """
    if not candidates or not isinstance(candidates, list):
        return []

    hop_le = [
        c for c in candidates
        if isinstance(c, dict) and c.get("diem_phu_hop", 0) >= min_score
    ]
    return sorted(hop_le, key=lambda c: c["diem_phu_hop"], reverse=True)


# ============================================================
# 🧩 NHÓM 2: HẸN LỊCH PHỎNG VẤN (Interview Scheduling)
# ============================================================

def check_interviewer_availability(interviewer_name: str, date: str) -> str:
    """
    Tra cứu các khung giờ còn trống của một interviewer trong một ngày cụ thể.

    Args:
        interviewer_name (str): Tên người phỏng vấn (ví dụ: 'Anh Minh')
        date (str): Ngày cần tra cứu, định dạng 'YYYY-MM-DD' (ví dụ: '2026-08-01')

    Returns:
        str: Chuỗi liệt kê các khung giờ trống, hoặc thông báo
             "LỖI: ..." nếu không tìm thấy interviewer hoặc không có lịch
             trống trong ngày đó.
    """
    if not interviewer_name or not isinstance(interviewer_name, str):
        return "LỖI: Thiếu tên interviewer (interviewer_name)."
    if not date or not isinstance(date, str):
        return "LỖI: Thiếu ngày cần tra cứu (date), định dạng 'YYYY-MM-DD'."

    key = interviewer_name.lower().strip()
    if key not in INTERVIEWER_SCHEDULE:
        return f"LỖI: Không tìm thấy lịch của interviewer '{interviewer_name}'."

    slots = INTERVIEWER_SCHEDULE[key].get(date)
    if not slots:
        return f"LỖI: {interviewer_name} không có khung giờ trống vào ngày {date}."

    return f"{interviewer_name} rảnh ngày {date} vào các khung giờ: {', '.join(slots)}."


def schedule_interview(candidate_name: str, interviewer_name: str,
                        date: str, time_slot: str) -> str:
    """
    Đặt lịch phỏng vấn giữa ứng viên và interviewer vào một khung giờ cụ thể,
    nếu khung giờ đó còn trống.

    Args:
        candidate_name (str): Tên ứng viên (ví dụ: 'Nguyễn Văn A')
        interviewer_name (str): Tên người phỏng vấn (ví dụ: 'Anh Minh')
        date (str): Ngày phỏng vấn, định dạng 'YYYY-MM-DD'
        time_slot (str): Khung giờ mong muốn, định dạng 'HH:MM' (ví dụ: '09:00')

    Returns:
        str: Thông báo đặt lịch thành công (gồm tên ứng viên, interviewer,
             ngày giờ), hoặc "LỖI: ..." nếu khung giờ không còn trống /
             interviewer không tồn tại.
    """
    if not all([candidate_name, interviewer_name, date, time_slot]) or not all(
        isinstance(x, str) for x in [candidate_name, interviewer_name, date, time_slot]
    ):
        return "LỖI: Thiếu hoặc sai kiểu tham số (cần đủ candidate_name, interviewer_name, date, time_slot dạng chuỗi)."

    key = interviewer_name.lower().strip()
    if key not in INTERVIEWER_SCHEDULE or date not in INTERVIEWER_SCHEDULE[key]:
        return f"LỖI: Không có dữ liệu lịch trống cho {interviewer_name} ngày {date}."

    slots = INTERVIEWER_SCHEDULE[key][date]
    if time_slot not in slots:
        return (f"LỖI: Khung giờ {time_slot} ngày {date} của {interviewer_name} "
                f"không còn trống. Các khung giờ trống: {', '.join(slots)}.")

    # Cập nhật mock data: bỏ khung giờ vừa đặt khỏi danh sách rảnh
    slots.remove(time_slot)
    BOOKED_INTERVIEWS.append({
        "ung_vien": candidate_name,
        "interviewer": interviewer_name,
        "ngay": date,
        "gio": time_slot,
    })

    return (f"Đặt lịch phỏng vấn thành công: {candidate_name} phỏng vấn với "
            f"{interviewer_name} vào lúc {time_slot} ngày {date}.")


def send_interview_invitation(candidate_email: str, interview_details: str) -> str:
    """
    Gửi (mô phỏng) thư mời phỏng vấn tới email của ứng viên.

    Args:
        candidate_email (str): Địa chỉ email ứng viên (ví dụ: 'a@gmail.com')
        interview_details (str): Nội dung/thông tin buổi phỏng vấn cần gửi
                                  (ví dụ: 'Phỏng vấn lúc 09:00 ngày 2026-08-01')

    Returns:
        str: Thông báo xác nhận đã gửi thư mời, hoặc "LỖI: ..." nếu email
             không hợp lệ (thiếu ký tự '@').
    """
    if not candidate_email or not isinstance(candidate_email, str) or "@" not in candidate_email:
        return f"LỖI: Địa chỉ email '{candidate_email}' không hợp lệ."

    return f"Đã gửi thư mời phỏng vấn tới {candidate_email}. Nội dung: {interview_details}"


# ============================================================
# 📜 ĐĂNG KÝ TOOL CHO AGENT
# ===========================================================

AVAILABLE_TOOLS = {
    "extract_resume_info": extract_resume_info,
    "match_resume_to_job": match_resume_to_job,
    "filter_candidates": filter_candidates,
    "check_interviewer_availability": check_interviewer_availability,
    "schedule_interview": schedule_interview,
    "send_interview_invitation": send_interview_invitation,
}
