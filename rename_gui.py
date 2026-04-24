import re
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
from pathlib import Path
import threading
import pdfplumber


def extract_partner(text):
    match = re.search(r"\(법인명\)\s+(.+?)\s+성명", text)
    if match:
        return match.group(1).strip()
    return "unknown"


def extract_date(text):
    match = re.search(r"작성일자\s+공급가액.+?\n(\d{4}-\d{2}-\d{2})", text, re.DOTALL)
    if match:
        return match.group(1).replace("-", "")
    match = re.search(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", text)
    if match:
        y, m, d = match.group(1), match.group(2).zfill(2), match.group(3).zfill(2)
        return f"{y}{m}{d}"
    return "unknown"


def extract_amount(text):
    match = re.search(r"작성일자\s+공급가액.+?\n\d{4}-\d{2}-\d{2}\s+([\d,]+)", text, re.DOTALL)
    if match:
        return match.group(1).replace(",", "")
    return "unknown"


def extract_info(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    return extract_partner(text), extract_date(text), extract_amount(text)


def rename_pdfs(folder, log):
    folder = Path(folder)
    pdf_files = list(folder.glob("*.pdf"))

    if not pdf_files:
        log("PDF 파일이 없습니다.")
        return

    success, fail = 0, 0
    for pdf_path in pdf_files:
        try:
            partner, date, amount = extract_info(pdf_path)
            new_name = f"{partner}_{date}_{amount}.pdf"
            new_path = pdf_path.parent / new_name

            if pdf_path == new_path:
                log(f"[건너뜀] {pdf_path.name} (이미 변환된 파일)")
                continue

            if new_path.exists():
                log(f"[충돌] {pdf_path.name} → {new_name} (동일한 이름이 이미 존재)")
                fail += 1
                continue

            pdf_path.rename(new_path)
            log(f"[완료] {pdf_path.name}\n      → {new_name}")
            success += 1
        except Exception as e:
            log(f"[오류] {pdf_path.name}: {e}")
            fail += 1

    log(f"\n총 {success}개 완료, {fail}개 실패")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("세금계산서 파일명 변환기")
        self.resizable(False, False)
        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}

        # 폴더 선택
        frame = tk.Frame(self)
        frame.pack(fill="x", **pad)

        tk.Label(frame, text="PDF 폴더:").pack(side="left")
        self.folder_var = tk.StringVar()
        tk.Entry(frame, textvariable=self.folder_var, width=45).pack(side="left", padx=6)
        tk.Button(frame, text="찾아보기", command=self._browse).pack(side="left")

        # 실행 버튼
        self.run_btn = tk.Button(self, text="변환 실행", width=20, bg="#4A90D9", fg="white",
                                 font=("", 10, "bold"), command=self._run)
        self.run_btn.pack(pady=6)

        # 로그창
        self.log_box = scrolledtext.ScrolledText(self, width=60, height=18, state="disabled",
                                                  font=("Consolas", 9))
        self.log_box.pack(padx=12, pady=(0, 12))

    def _browse(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_var.set(folder)

    def _log(self, msg):
        self.log_box.config(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    def _run(self):
        folder = self.folder_var.get().strip()
        if not folder:
            messagebox.showwarning("알림", "PDF 폴더를 선택해주세요.")
            return

        self.run_btn.config(state="disabled", text="변환 중...")
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.config(state="disabled")

        def task():
            rename_pdfs(folder, lambda msg: self.after(0, self._log, msg))
            self.after(0, lambda: self.run_btn.config(state="normal", text="변환 실행"))

        threading.Thread(target=task, daemon=True).start()


if __name__ == "__main__":
    App().mainloop()
