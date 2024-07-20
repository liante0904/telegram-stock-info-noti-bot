class ReportSendingHistory:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def insert_report(self, report_data):
        insert_query = """
        INSERT INTO REPORT_SENDING_HISTORY (FIRM_NM, REPORT_TITLE, REPORT_COMPANY_NAME, REPORT_INDUSTRY, 
                                            REPORT_TYPE_NM, REPORT_TYPE, URL_LINK, CREATED_AT, UPDATED_AT)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.db_manager.execute_insert_query(insert_query, report_data)

    def select_all_reports(self):
        select_query = "SELECT * FROM REPORT_SENDING_HISTORY"
        records = self.db_manager.execute_select_query(select_query)
        print("Total number of rows in REPORT_SENDING_HISTORY is: ", len(records))
        for row in records:
            print(row)
