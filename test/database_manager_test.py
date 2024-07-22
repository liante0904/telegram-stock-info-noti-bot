from db.database_manager import DatabaseManager
from models.report_sending_history import ReportSendingHistory
import wget
if __name__ == "__main__":
    wget.download(url='https://rcv.kbsec.com/streamdocs/pdfview?id=B520190322125512762443&url=aHR0cDovL3JkYXRhLmtic2VjLmNvbS9wZGZfZGF0YS8yMDI0MDcxMDEwMDYyMDEwM0sucGRm', out='ATTACH_FILE_NAME.pdf')
    
    
    # 데이터베이스 URL (형식: mysql://username:password@hostname/dbname)
    db_url = "mysql://b764205237e190:daf823f4@140.238.13.123/telegrambot?reconnect=true"

    db_manager = DatabaseManager(db_url)
    
    # 데이터베이스 연결
    db_manager.open_connect()
    
    # ReportSendingHistory 클래스 인스턴스 생성
    report_history = ReportSendingHistory(db_manager)
    
    # # 데이터 삽입
    # report_data = ("Firm A", "Report Title", "Company Name", "Industry", "Type Name", "Type", "http://example.com", "2024-07-09 10:00:00", "2024-07-09 10:00:00")
    # report_history.insert_report(report_data)
    
    # 데이터 조회
    report_history.select_all_reports()

    # 특정 REPORT_ID로 데이터 조회 및 출력
    report_id = 1  # 조회하고자 하는 REPORT_ID 값
    cursor = db_manager.cursor

    try:
        query = "SELECT * FROM REPORT_SENDING_HISTORY WHERE REPORT_ID = %s"
        cursor.execute(query, (report_id,))
        result = cursor.fetchone()

        if result:
            print(f"\nDetails of REPORT_ID {report_id}:")
            for column, value in result.items():
                print(f"{column}: {value}")
        else:
            print(f"No record found with REPORT_ID {report_id}")

    except Exception as e:
        print("Error executing SELECT query:", e)
    
    # 데이터베이스 연결 종료
    db_manager.close_connect()
