# models/OracleManagerSQL.py (Legacy Compatibility Layer)
# 이 파일은 하위 호환성을 위해 유지됩니다. 신규 코드는 models.OracleManager를 사용하세요.

from models.OracleManager import OracleManager as IntegratedOracleManager

class OracleManagerSQL(IntegratedOracleManager):
    """
    구형 OracleManagerSQL의 인터페이스를 유지하면서 내부적으로 통합된 OracleManager를 사용합니다.
    """
    def __init__(self):
        super().__init__()

    def open_connection(self):
        # 신규 매니저는 필요할 때마다 연결을 열고 닫으므로 명시적 open은 무시하거나 
        # 하위 호환을 위해 더미로 둡니다.
        pass

    def close_connection(self):
        pass

    def insert_json_data_list(self, json_data_list, table_name=None, full_insert=False):
        if table_name is None:
            table_name = self.main_table_name
        # 비동기 메서드를 동기 방식으로 래핑하여 호출 (필요 시)
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 이미 루프가 돌아가고 있다면 (비동기 환경)
            return loop.create_task(super().insert_json_data_list(json_data_list))
        else:
            return asyncio.run(super().insert_json_data_list(json_data_list))
